"""
Core Agent Logic — Orchestrates state extraction, retrieval, and LLM generation.
"""
import os
from typing import Any, Dict, List, Optional, Tuple

from groq import Groq

from app.catalog import CATALOG, validate_recommendation, search_by_name
from app.prompts import (
    SYSTEM_PROMPT,
    REFUSAL_RESPONSES,
    build_comparison_prompt,
    detect_refusal_topic,
)
from app.retrieval import retrieve_and_rank, apply_delta_update, format_recommendation
from app.state import extract_state, needs_clarification, build_clarification_question

# ─── LLM Client Setup ────────────────────────────────────────────────────────
_CLIENT = None


def get_model():
    """Return a callable that generates content using Groq."""
    global _CLIENT
    if _CLIENT is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY environment variable not set")
        _CLIENT = Groq(api_key=api_key)
    return _CLIENT


def _generate(prompt: str) -> str:
    """Generate content using Llama 3.3 70b on Groq."""
    client = get_model()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=0.1,
        max_tokens=2048,
    )
    return response.choices[0].message.content


# ─── Intent Detection ────────────────────────────────────────────────────────

CONFIRMATION_KEYWORDS = [
    "that's it", "that's good", "confirmed", "perfect", "great", "thank you",
    "thanks", "that works", "keep", "locked in", "locking it in", "done",
    "covers it", "good to go", "all set", "looks good",
]

COMPARISON_PATTERNS = [
    "difference between", "compare", "vs", "versus", "which is better",
    "how does", "differ from", "distinguish",
]


def detect_intent(messages: List[Dict], state: Dict) -> str:
    """
    Detect conversation intent from latest user message.
    Returns: 'clarification_needed' | 'recommend' | 'refine' | 'compare' | 'confirm' | 'refuse'
    """
    if not messages:
        return "clarification_needed"

    last_user = next(
        (m for m in reversed(messages) if m.get("role") == "user"), None
    )
    if not last_user:
        return "recommend"

    text = last_user.get("content", "").lower()

    # Check refusals first
    refusal = detect_refusal_topic(text)
    if refusal:
        return f"refuse:{refusal}"

    # Comparison
    if any(p in text for p in COMPARISON_PATTERNS) and state.get("comparison_request"):
        return "compare"

    # Confirmation / end conversation
    if any(kw in text for kw in CONFIRMATION_KEYWORDS):
        return "confirm"

    # Refinement (if we've already recommended)
    has_prior_recs = any(
        m.get("role") == "assistant"
        and (
            "| Name |" in m.get("content", "")
            or "shl.com" in m.get("content", "")
        )
        for m in messages
    )
    if has_prior_recs and any(
        kw in text
        for kw in [
            "add", "also include", "include", "remove", "drop", "replace",
            "update", "change", "instead", "swap", "without"
        ]
    ):
        return "refine"

    # Needs clarification
    turn_count = state.get("turn_count", 0)
    if needs_clarification(state, turn_count):
        return "clarification_needed"

    return "recommend"


# ─── Hallucination Validation ────────────────────────────────────────────────

def _validate_and_filter_recs(recs: List[Dict]) -> List[Dict]:
    """Filter recommendations to only those that exist in catalog."""
    valid = []
    for rec in recs:
        if validate_recommendation(rec):
            valid.append(rec)
    return valid


# ─── Comparison Handler ──────────────────────────────────────────────────────

def _handle_comparison(state: Dict, messages: List[Dict]) -> Tuple[str, Optional[List], bool]:
    """Generate a comparison response grounded in catalog facts."""
    comp = state.get("comparison_request")
    if not comp:
        return "I couldn't identify the two assessments to compare. Please specify the exact names.", None, False

    item_a = search_by_name(comp["item_a"])
    item_b = search_by_name(comp["item_b"])

    if not item_a or not item_b:
        missing = []
        if not item_a:
            missing.append(comp["item_a"])
        if not item_b:
            missing.append(comp["item_b"])
        names = " and ".join(missing)
        return (
            f"I couldn't find '{names}' in the SHL catalog. "
            "Please check the assessment names and try again.",
            None,
            False,
        )

    comparison_prompt = build_comparison_prompt(item_a, item_b, messages[-1].get("content", ""))
    response_text = _generate(comparison_prompt)
    return response_text, None, False


# ─── Table Parser (for extracting recs from LLM output) ─────────────────────

def _parse_table_recommendations(text: str) -> List[Dict]:
    """Extract recommendations from a markdown table in LLM output."""
    recs = []
    lines = text.split("\n")
    header_found = False

    for line in lines:
        if "| Name |" in line or "| # |" in line:
            header_found = True
            continue
        if header_found and line.startswith("|") and "---" not in line:
            parts = [p.strip() for p in line.split("|")]
            parts = [p for p in parts if p]
            if len(parts) >= 3:
                # Try to extract name and URL
                name = ""
                url = ""
                test_type = ""

                for i, p in enumerate(parts):
                    if "shl.com" in p:
                        # URL might be in angle brackets
                        import re
                        url_match = re.search(r'https://[^\s\)>]+', p)
                        if url_match:
                            url = url_match.group(0).rstrip("/") + "/"
                    elif i == 1 and not name:
                        name = p
                    elif i == 2 and not test_type:
                        test_type = p

                if name and url:
                    recs.append({
                        "name": name,
                        "url": url,
                        "test_type": test_type,
                    })
    return recs


# ─── Main Agent Logic ────────────────────────────────────────────────────────

def build_table_from_items(items: List[Dict]) -> str:
    """Build markdown recommendation table from catalog items."""
    rows = [
        "| # | Name | Test Type | Keys | Duration | Languages | URL |",
        "|---|------|-----------|------|----------|-----------|-----|",
    ]
    for i, item in enumerate(items, 1):
        rec = format_recommendation(item, i)
        row = (
            f"| {i} | {rec['name']} | {rec['test_type']} | "
            f"{rec['keys']} | {rec['duration']} | {rec['languages']} | "
            f"<{rec['url']}> |"
        )
        rows.append(row)
    return "\n".join(rows)


def run_agent(messages: List[Dict]) -> Tuple[str, Optional[List[Dict]], bool]:
    """
    Main agent orchestration function.

    Args:
        messages: Full conversation history

    Returns:
        (response_text, recommendations_list, end_of_conversation)
    """
    # ── 1. Reconstruct state ──────────────────────────────────────────────
    state = extract_state(messages)
    intent = detect_intent(messages, state)

    # ── 2. Handle refusal ─────────────────────────────────────────────────
    if intent.startswith("refuse:"):
        category = intent.split(":", 1)[1]
        return REFUSAL_RESPONSES.get(category, REFUSAL_RESPONSES["off_topic"]), None, False

    # ── 3. Handle comparison ──────────────────────────────────────────────
    if intent == "compare":
        text, recs, eoc = _handle_comparison(state, messages)
        return text, recs, eoc

    # ── 4. Handle clarification needed ───────────────────────────────────
    if intent == "clarification_needed":
        question = build_clarification_question(state, state.get("turn_count", 0))
        if question:
            return question, [], False
        # Fallback: proceed to recommend
        intent = "recommend"

    # ── 5. Handle confirmation / end of conversation ──────────────────────
    if intent == "confirm":
        # Re-produce the last recommendations as final
        candidates = retrieve_and_rank(state, messages, top_k=10)
        if candidates:
            table = build_table_from_items(candidates)
            response = f"Confirmed.\n\n{table}"
            recs_out = [
                {"name": c["name"], "url": c["url"], "test_type": ",".join(c.get("test_type", []))}
                for c in candidates
            ]
            return response, recs_out, True
        return "Understood. Let me know if you need anything else.", [], True

    # ── 6. Handle refinement ──────────────────────────────────────────────
    if intent == "refine":
        candidates = retrieve_and_rank(state, messages, top_k=10)
    else:
        # ── 7. Standard recommendation ────────────────────────────────────
        candidates = retrieve_and_rank(state, messages, top_k=10)

    if not candidates:
        return (
            "I wasn't able to find relevant assessments in the catalog for your requirements. "
            "Could you give me more details about the role and what you're looking to measure?",
            [],
            False,
        )

    # ── 8. Build prompt for LLM to generate the final response ───────────
    # Format catalog candidates for LLM
    catalog_block = ""
    for i, item in enumerate(candidates, 1):
        langs_list = item.get("languages", [])
        langs = ", ".join(langs_list[:2]) + (f" (+{len(langs_list)-2} more)" if len(langs_list) > 2 else "") if langs_list else "—"
        catalog_block += (
            f"{i}. {item['name']} | Type: {','.join(item.get('test_type',[]))} | "
            f"Duration: {item.get('duration','—')} | Languages: {langs} | "
            f"{', '.join(item.get('test_type_labels',[]))}\n"
            f"   URL: {item['url']}\n"
            f"   {item.get('description','')[:100]}\n\n"
        )

    # Build conversation summary for LLM
    conv_summary = "\n".join(
        f"{'User' if m['role']=='user' else 'Agent'}: {m['content'][:200]}"
        for m in messages[-8:]  # Last 8 turns for context
    )

    is_refinement = intent == "refine"
    is_final = state.get("turn_count", 0) >= 8

    llm_prompt = f"""You are producing the next response in an SHL assessment recommendation conversation.

CONVERSATION (recent):
{conv_summary}

EXTRACTED CONTEXT:
- Role: {state.get('role_categories', [])}
- Skills: {state.get('technical_skills', [])}
- Seniority: {state.get('seniority', 'unknown')}
- Personality needed: {state.get('personality_focus', False)}
- Cognitive needed: {state.get('cognitive_focus', False)}
- Use case: {state.get('use_case', 'selection')}
- Safety critical: {state.get('safety_critical', False)}

PRE-RETRIEVED CATALOG ITEMS (use ONLY these):
{catalog_block}

INSTRUCTION:
{"Update the shortlist based on the refinement request." if is_refinement else "Generate the assessment battery recommendation."}
1. Select the most relevant 2-8 items from the pre-retrieved list above
2. Write 1-2 sentences of rationale. DO NOT use robotic phrases like "Based on the extracted context" or "Based on the user's input". Be natural, engaging, and conversational. Directly address the user (e.g. "Here is a recommended assessment battery for your Software Engineer role...").
3. Then output the markdown table with columns: # | Name | Test Type | Keys | Duration | Languages | URL
4. Use EXACT names and URLs from the catalog items listed above — do not modify them
5. For professional/senior selection, include OPQ32r unless excluded
"""

    response_text = _generate(llm_prompt)

    # ── 9. Parse and validate recommendations from LLM output ─────────────
    parsed_recs = _parse_table_recommendations(response_text)
    validated_recs = _validate_and_filter_recs(parsed_recs)

    # If LLM didn't produce valid recs, fall back to our retrieval results
    if not validated_recs:
        # Use retrieval results directly
        table = build_table_from_items(candidates[:8])
        response_text = f"{response_text.split('|')[0].strip()}\n\n{table}"
        recs_out = [
            {"name": c["name"], "url": c["url"], "test_type": ",".join(c.get("test_type", []))}
            for c in candidates[:8]
        ]
    else:
        recs_out = validated_recs

    # Determine end of conversation
    end_of_conv = is_final and intent != "compare"

    return response_text, recs_out, end_of_conv
