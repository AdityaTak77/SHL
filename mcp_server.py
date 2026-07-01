"""
SHL Assessment Recommender — MCP Server
Exposes SHL catalog search and recommendation tools via the Model Context Protocol.

Usage with Claude Desktop or any MCP client:
  python mcp_server.py

Tools exposed:
  - search_assessments(query, top_k)     → BM25 + metadata search
  - get_assessment(name)                  → single assessment details
  - list_test_types()                     → catalog of test type codes
  - recommend_battery(role, seniority, skills, ...)  → full recommendation
  - compare_assessments(name_a, name_b)  → side-by-side comparison
  - list_all_assessments()               → full catalog listing
"""
import json
import os
import sys
from typing import Any, Dict, List, Optional

# Add parent dir to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
    ListToolsResult,
)

from app.catalog import CATALOG, search_by_name, validate_recommendation
from app.retrieval import retrieve_and_rank, BM25, get_bm25_index, format_recommendation
from app.state import extract_state

# ─── MCP Server Setup ────────────────────────────────────────────────────────
server = Server("shl-assessment-recommender")

# ─── Tool Definitions ────────────────────────────────────────────────────────

TOOLS = [
    Tool(
        name="search_assessments",
        description=(
            "Search the SHL Individual Test Solutions catalog using a natural language query. "
            "Returns ranked assessments matching the query. Use this to find relevant assessments "
            "for a given role, skill, or context."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query, e.g. 'Java developer mid-level cognitive ability'"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (1-20, default 10)",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 20
                },
                "test_type_filter": {
                    "type": "string",
                    "description": "Filter by test type code: A=Ability, B=Biodata/SJT, C=Competencies, D=Development, K=Knowledge, P=Personality, S=Simulations. Leave empty for all.",
                    "default": ""
                }
            },
            "required": ["query"]
        }
    ),
    Tool(
        name="get_assessment",
        description=(
            "Get full details for a specific SHL assessment by name. "
            "Returns all catalog metadata including description, duration, languages, competencies, and URL."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Assessment name (exact or partial), e.g. 'OPQ32r' or 'Verify Interactive G+'"
                }
            },
            "required": ["name"]
        }
    ),
    Tool(
        name="recommend_battery",
        description=(
            "Generate a full assessment battery recommendation for a given hiring scenario. "
            "Combines role, seniority, skills, and other context to return the best-fit assessments."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "description": "Job role or title, e.g. 'Senior Java Developer', 'Contact Centre Agent', 'CXO Executive'"
                },
                "seniority": {
                    "type": "string",
                    "description": "Seniority level: entry, graduate, professional, manager, director, executive",
                    "enum": ["entry", "graduate", "professional", "manager", "director", "executive"]
                },
                "skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Technical skills required, e.g. ['Java', 'Spring', 'AWS']"
                },
                "include_personality": {
                    "type": "boolean",
                    "description": "Whether to include personality/behavioral assessments (default: true for professional+)",
                    "default": True
                },
                "include_cognitive": {
                    "type": "boolean",
                    "description": "Whether to include cognitive ability assessments",
                    "default": True
                },
                "use_case": {
                    "type": "string",
                    "description": "Purpose: selection (hiring), development (learning), or audit",
                    "enum": ["selection", "development", "audit"],
                    "default": "selection"
                },
                "safety_critical": {
                    "type": "boolean",
                    "description": "Whether role involves safety-critical responsibilities",
                    "default": False
                },
                "language": {
                    "type": "string",
                    "description": "Required assessment language, e.g. 'English', 'Spanish', 'French'",
                    "default": ""
                },
                "top_k": {
                    "type": "integer",
                    "description": "Max recommendations to return (1-10)",
                    "default": 8,
                    "minimum": 1,
                    "maximum": 10
                }
            },
            "required": ["role"]
        }
    ),
    Tool(
        name="compare_assessments",
        description=(
            "Compare two SHL assessments side by side using catalog data only. "
            "Returns a structured comparison of their features, duration, languages, and use cases."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name_a": {
                    "type": "string",
                    "description": "First assessment name (exact or partial)"
                },
                "name_b": {
                    "type": "string",
                    "description": "Second assessment name (exact or partial)"
                }
            },
            "required": ["name_a", "name_b"]
        }
    ),
    Tool(
        name="list_test_types",
        description="List all SHL test type codes with their meanings and example assessments.",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="list_all_assessments",
        description=(
            "Return the complete SHL Individual Test Solutions catalog. "
            "Optionally filter by test type. Useful for browsing or building custom retrieval."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "test_type_filter": {
                    "type": "string",
                    "description": "Filter by type code: A, B, C, D, K, P, or S. Empty for all.",
                    "default": ""
                },
                "include_details": {
                    "type": "boolean",
                    "description": "Include full details (slower) vs summary only (faster)",
                    "default": False
                }
            },
            "required": []
        }
    ),
]

# ─── Tool Handlers ────────────────────────────────────────────────────────────

def _format_item_full(item: Dict) -> str:
    """Format a catalog item as readable text."""
    langs = item.get("languages", [])
    lang_str = ", ".join(langs[:5]) + (f" (+{len(langs)-5} more)" if len(langs) > 5 else "")
    return (
        f"**{item['name']}**\n"
        f"- URL: {item['url']}\n"
        f"- Test Type: {', '.join(item.get('test_type_labels', []))} ({', '.join(item.get('test_type', []))})\n"
        f"- Duration: {item.get('duration', '—')}\n"
        f"- Description: {item.get('description', 'No description available')}\n"
        f"- Competencies: {', '.join(item.get('competencies', [])[:6])}\n"
        f"- Technical Domains: {', '.join(item.get('technical_domains', []))}\n"
        f"- Job Levels: {', '.join(item.get('job_levels', []))}\n"
        f"- Use Cases: {', '.join(item.get('use_cases', []))}\n"
        f"- Languages: {lang_str}\n"
        f"- Assessment Family: {item.get('assessment_family', '—')}\n"
    )


def _format_item_summary(item: Dict) -> str:
    """Format a catalog item as a brief summary."""
    return (
        f"- **{item['name']}** | {', '.join(item.get('test_type', []))} | "
        f"{item.get('duration', '—')} | {item['url']}"
    )


@server.list_tools()
async def list_tools() -> ListToolsResult:
    return ListToolsResult(tools=TOOLS)


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    try:
        if name == "search_assessments":
            return await _search_assessments(**arguments)
        elif name == "get_assessment":
            return await _get_assessment(**arguments)
        elif name == "recommend_battery":
            return await _recommend_battery(**arguments)
        elif name == "compare_assessments":
            return await _compare_assessments(**arguments)
        elif name == "list_test_types":
            return await _list_test_types()
        elif name == "list_all_assessments":
            return await _list_all_assessments(**arguments)
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")]
            )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error executing tool '{name}': {str(e)}")]
        )


async def _search_assessments(
    query: str,
    top_k: int = 10,
    test_type_filter: str = ""
) -> CallToolResult:
    """BM25 + metadata search."""
    # Build synthetic state from query
    msgs = [{"role": "user", "content": query}]
    state = extract_state(msgs)
    results = retrieve_and_rank(state, msgs, top_k=min(top_k, 20))

    # Apply test type filter if provided
    if test_type_filter:
        filter_code = test_type_filter.upper().strip()
        results = [r for r in results if filter_code in r.get("test_type", [])]

    if not results:
        return CallToolResult(
            content=[TextContent(type="text", text=f"No assessments found for query: '{query}'")]
        )

    lines = [f"## Search Results for: '{query}'\n\nFound {len(results)} assessments:\n"]
    for i, item in enumerate(results, 1):
        rec = format_recommendation(item, i)
        lines.append(
            f"{i}. **{rec['name']}**\n"
            f"   - Test Type: {rec['keys']} ({rec['test_type']})\n"
            f"   - Duration: {rec['duration']}\n"
            f"   - URL: {item['url']}\n"
            f"   - Score: {item.get('_final_score', 0):.3f}\n"
        )

    return CallToolResult(content=[TextContent(type="text", text="\n".join(lines))])


async def _get_assessment(name: str) -> CallToolResult:
    """Get full details for a specific assessment."""
    item = search_by_name(name)
    if not item:
        # Try broader search
        bm25 = get_bm25_index()
        results = bm25.get_top_k(name, k=3)
        if results:
            suggestions = "\n".join(f"  - {r['name']}" for r in results)
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Assessment '{name}' not found. Did you mean:\n{suggestions}"
                )]
            )
        return CallToolResult(
            content=[TextContent(type="text", text=f"Assessment '{name}' not found in catalog.")]
        )

    return CallToolResult(
        content=[TextContent(type="text", text=_format_item_full(item))]
    )


async def _recommend_battery(
    role: str,
    seniority: str = "professional",
    skills: List[str] = None,
    include_personality: bool = True,
    include_cognitive: bool = True,
    use_case: str = "selection",
    safety_critical: bool = False,
    language: str = "",
    top_k: int = 8,
) -> CallToolResult:
    """Generate a full recommendation battery."""
    skills = skills or []

    # Build state directly
    state = {
        "role": role.lower().replace(" ", "_"),
        "role_categories": [role.lower()],
        "seniority": seniority,
        "technical_skills": [s.lower() for s in skills],
        "personality_focus": include_personality,
        "cognitive_focus": include_cognitive,
        "simulation_focus": False,
        "sjt_focus": False,
        "language_requirements": [language.lower()] if language else [],
        "safety_critical": safety_critical,
        "use_case": use_case,
        "volume": None,
        "excluded_assessments": [],
        "confirmed_assessments": [],
        "previous_recommendations": [],
        "comparison_request": None,
        "turn_count": 2,
        "raw_context": [{"role": "user", "text": f"Hiring {role} {seniority} {' '.join(skills)}"}],
        "experience_years": None,
        "industry": None,
        "bilingual": False,
    }

    # Build synthetic messages
    msgs = [{"role": "user", "content": f"I need to hire a {seniority} {role}. Skills: {', '.join(skills) or 'general'}. Use case: {use_case}."}]

    candidates = retrieve_and_rank(state, msgs, top_k=top_k)

    if not candidates:
        return CallToolResult(
            content=[TextContent(type="text", text=f"No assessments found for: {role} ({seniority})")]
        )

    # Format as markdown table
    lines = [
        f"## Recommended Assessment Battery\n",
        f"**Role:** {role} | **Seniority:** {seniority} | **Use Case:** {use_case}\n",
        f"**Skills:** {', '.join(skills) or 'None specified'} | **Safety Critical:** {safety_critical}\n\n",
        "| # | Assessment | Type | Duration | URL |",
        "|---|-----------|------|----------|-----|",
    ]
    recs_out = []
    for i, item in enumerate(candidates, 1):
        rec = format_recommendation(item, i)
        lines.append(
            f"| {i} | {rec['name']} | {rec['keys']} | {rec['duration']} | {item['url']} |"
        )
        recs_out.append({"name": item["name"], "url": item["url"], "test_type": rec["test_type"]})

    lines.append(f"\n*{len(candidates)} assessments recommended from SHL catalog.*")

    return CallToolResult(
        content=[TextContent(type="text", text="\n".join(lines))]
    )


async def _compare_assessments(name_a: str, name_b: str) -> CallToolResult:
    """Side-by-side comparison using catalog data only."""
    item_a = search_by_name(name_a)
    item_b = search_by_name(name_b)

    errors = []
    if not item_a:
        errors.append(f"'{name_a}' not found in catalog")
    if not item_b:
        errors.append(f"'{name_b}' not found in catalog")

    if errors:
        return CallToolResult(
            content=[TextContent(type="text", text="Cannot compare: " + "; ".join(errors))]
        )

    def _get(item, key, default="—"):
        val = item.get(key, default)
        if isinstance(val, list):
            return ", ".join(val[:5]) if val else "—"
        return str(val) if val else "—"

    table = [
        f"## Comparison: {item_a['name']} vs {item_b['name']}\n",
        f"| Feature | {item_a['name']} | {item_b['name']} |",
        f"|---------|{'—'*len(item_a['name'])}|{'—'*len(item_b['name'])}|",
        f"| Test Type | {_get(item_a, 'test_type_labels')} | {_get(item_b, 'test_type_labels')} |",
        f"| Duration | {_get(item_a, 'duration')} | {_get(item_b, 'duration')} |",
        f"| Job Levels | {_get(item_a, 'job_levels')} | {_get(item_b, 'job_levels')} |",
        f"| Languages | {len(item_a.get('languages', []))} available | {len(item_b.get('languages', []))} available |",
        f"| Competencies | {_get(item_a, 'competencies')} | {_get(item_b, 'competencies')} |",
        f"| Use Cases | {_get(item_a, 'use_cases')} | {_get(item_b, 'use_cases')} |",
        f"| Family | {_get(item_a, 'assessment_family')} | {_get(item_b, 'assessment_family')} |",
        f"| URL | {item_a['url']} | {item_b['url']} |",
        f"\n### {item_a['name']} — Description",
        item_a.get('description', 'No description available'),
        f"\n### {item_b['name']} — Description",
        item_b.get('description', 'No description available'),
    ]

    return CallToolResult(
        content=[TextContent(type="text", text="\n".join(table))]
    )


async def _list_test_types() -> CallToolResult:
    """List all test type codes."""
    # Count items per type
    type_counts: Dict[str, int] = {}
    for item in CATALOG:
        for tt in item.get("test_type", []):
            type_counts[tt] = type_counts.get(tt, 0) + 1

    # Sample items per type
    type_samples: Dict[str, List[str]] = {}
    for item in CATALOG:
        for tt in item.get("test_type", []):
            if tt not in type_samples:
                type_samples[tt] = []
            if len(type_samples[tt]) < 3:
                type_samples[tt].append(item["name"])

    TYPE_DESCRIPTIONS = {
        "A": "Ability & Aptitude — cognitive reasoning, numerical, verbal, inductive tests",
        "B": "Biodata & Situational Judgment — SJT, scenario-based, past behavior",
        "C": "Competencies — structured competency frameworks",
        "D": "Development & 360 — feedback, coaching, growth tools",
        "K": "Knowledge & Skills — technical domain tests (Java, SQL, AWS, etc.)",
        "P": "Personality & Behavior — OPQ, trait-based, behavioral styles",
        "S": "Simulations — live coding, role plays, interactive exercises",
    }

    lines = ["## SHL Test Type Codes\n"]
    for code in sorted(TYPE_DESCRIPTIONS.keys()):
        count = type_counts.get(code, 0)
        samples = type_samples.get(code, [])
        lines.append(
            f"**{code}** — {TYPE_DESCRIPTIONS[code]}\n"
            f"  - Count in catalog: {count}\n"
            f"  - Examples: {', '.join(samples)}\n"
        )

    return CallToolResult(content=[TextContent(type="text", text="\n".join(lines))])


async def _list_all_assessments(
    test_type_filter: str = "",
    include_details: bool = False
) -> CallToolResult:
    """List all assessments, optionally filtered."""
    items = CATALOG
    if test_type_filter:
        code = test_type_filter.upper().strip()
        items = [i for i in items if code in i.get("test_type", [])]

    if not items:
        return CallToolResult(
            content=[TextContent(type="text", text=f"No assessments found with type filter: '{test_type_filter}'")]
        )

    lines = [f"## SHL Catalog — {len(items)} assessments{f' (type: {test_type_filter})' if test_type_filter else ''}\n"]

    if include_details:
        for item in items:
            lines.append(_format_item_full(item))
            lines.append("---")
    else:
        for item in items:
            lines.append(_format_item_summary(item))

    return CallToolResult(content=[TextContent(type="text", text="\n".join(lines))])


# ─── Entry Point ──────────────────────────────────────────────────────────────

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
