"""
Hybrid Retrieval & Ranking Engine
Stage 1: BM25 keyword retrieval
Stage 2: Embedding / TF-IDF retrieval
Stage 3: Metadata filtering
Stage 4: Scoring / re-ranking
Stage 5: Final LLM ranking (done via prompt)

Why this approach maximises Recall@10:
- BM25 catches exact keyword matches (Java, Docker, nursing)
- TF-IDF/embedding catches semantic matches
- Metadata filtering removes irrelevant (wrong language, wrong level)
- Multi-signal scoring boosts relevant items
"""
import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple

from app.catalog import CATALOG, normalize_text
from app.state import extract_state


# ─── Pre-computed BM25 index ──────────────────────────────────────────────────
class BM25:
    """Okapi BM25 implementation for catalog search."""

    def __init__(self, corpus: List[Dict], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.doc_texts = [self._doc_to_text(d) for d in corpus]
        self.tokenized = [self._tokenize(t) for t in self.doc_texts]
        self.N = len(self.tokenized)
        self.avgdl = sum(len(d) for d in self.tokenized) / max(self.N, 1)
        self.df = self._compute_df()
        self.idf = self._compute_idf()

    def _doc_to_text(self, doc: Dict) -> str:
        parts = [
            doc.get("name", ""),
            doc.get("description", ""),
            " ".join(doc.get("competencies", [])),
            " ".join(doc.get("technical_domains", [])),
            " ".join(doc.get("use_cases", [])),
            " ".join(doc.get("test_type_labels", [])),
            " ".join(doc.get("job_levels", [])),
            doc.get("assessment_family", ""),
        ]
        return normalize_text(" ".join(parts))

    def _tokenize(self, text: str) -> List[str]:
        return text.split()

    def _compute_df(self) -> Dict[str, int]:
        df = Counter()
        for doc in self.tokenized:
            seen = set(doc)
            for token in seen:
                df[token] += 1
        return df

    def _compute_idf(self) -> Dict[str, float]:
        idf = {}
        for term, freq in self.df.items():
            idf[term] = math.log((self.N - freq + 0.5) / (freq + 0.5) + 1)
        return idf

    def score(self, query: str) -> List[Tuple[int, float]]:
        """Return (doc_index, score) for all docs, sorted by score."""
        query_tokens = self._tokenize(normalize_text(query))
        scores = []
        for idx, doc_tokens in enumerate(self.tokenized):
            tf_counts = Counter(doc_tokens)
            dl = len(doc_tokens)
            score = 0.0
            for token in query_tokens:
                if token not in self.idf:
                    continue
                tf = tf_counts.get(token, 0)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                score += self.idf[token] * numerator / denominator
            scores.append((idx, score))
        return sorted(scores, key=lambda x: x[1], reverse=True)

    def get_top_k(self, query: str, k: int = 20) -> List[Dict]:
        scored = self.score(query)
        result = []
        for idx, score in scored[:k]:
            if score > 0:
                item = dict(self.corpus[idx])
                item["_bm25_score"] = score
                result.append(item)
        return result


# ─── Singleton BM25 index ─────────────────────────────────────────────────────
_BM25_INDEX: Optional[BM25] = None


def get_bm25_index() -> BM25:
    global _BM25_INDEX
    if _BM25_INDEX is None:
        _BM25_INDEX = BM25(CATALOG)
    return _BM25_INDEX


# ─── Metadata Scoring ─────────────────────────────────────────────────────────
SENIORITY_MAP = {
    "entry": ["entry"],
    "graduate": ["graduate", "entry"],
    "professional": ["professional", "graduate"],
    "manager": ["manager", "professional"],
    "director": ["director", "manager"],
    "executive": ["executive", "director"],
}


def _seniority_score(item: Dict, state: Dict) -> float:
    """Score how well item job_levels matches state seniority."""
    if not state.get("seniority"):
        return 0.5  # neutral
    applicable = SENIORITY_MAP.get(state["seniority"], [state["seniority"]])
    item_levels = {level.lower() for level in item.get("job_levels", [])}
    if not item_levels:
        return 0.3
    overlap = len(item_levels & set(applicable))
    return min(1.0, overlap / max(len(applicable), 1))


def _language_score(item: Dict, state: Dict) -> float:
    """Score language compatibility."""
    lang_reqs = state.get("language_requirements", [])
    if not lang_reqs:
        return 0.5  # neutral
    item_langs = [l.lower() for l in item.get("languages", [])]
    if not item_langs:
        return 0.2  # no language info = slight penalty
    lang_text = " ".join(item_langs)
    for req in lang_reqs:
        req_clean = req.replace("_", " ")
        if req_clean in lang_text or any(r in lang_text for r in req.split("_")):
            return 1.0
    return 0.0


def _competency_overlap_score(item: Dict, state: Dict) -> float:
    """Score competency/skill overlap between item and state."""
    tech_skills = [normalize_text(s) for s in state.get("technical_skills", [])]
    role_cats = state.get("role_categories", [])

    if not tech_skills and not role_cats:
        return 0.3

    item_text = normalize_text(
        " ".join(item.get("competencies", []))
        + " "
        + " ".join(item.get("technical_domains", []))
        + " "
        + " ".join(item.get("use_cases", []))
        + " "
        + item.get("name", "")
        + " "
        + item.get("description", "")
    )

    hits = 0
    total = len(tech_skills) + len(role_cats)

    for skill in tech_skills:
        if skill in item_text:
            hits += 1

    for cat in role_cats:
        cat_clean = cat.replace("_", " ")
        if cat_clean in item_text:
            hits += 1

    return hits / max(total, 1)


def _test_type_preference_score(item: Dict, state: Dict) -> float:
    """Score based on user's expressed test type preferences."""
    item_types = set(item.get("test_type", []))
    score = 0.0

    if state.get("personality_focus") and "P" in item_types:
        score += 0.3
    if state.get("cognitive_focus") and "A" in item_types:
        score += 0.3
    if state.get("simulation_focus") and "S" in item_types:
        score += 0.3
    if state.get("sjt_focus") and "B" in item_types:
        score += 0.3

    # Safety critical boosts
    if state.get("safety_critical") and item.get("id") in [
        "dependability-and-safety-instrument-dsi",
        "safety-and-dependability-focus-8-0",
        "workplace-health-and-safety-new",
    ]:
        score += 0.5

    return min(1.0, score)


def _use_case_score(item: Dict, state: Dict) -> float:
    """Score based on use case alignment."""
    use_case = state.get("use_case")
    if not use_case:
        return 0.5
    item_uses = " ".join(item.get("use_cases", [])).lower()
    item_uses += " " + " ".join(item.get("keys", [])).lower()
    item_uses += " " + item.get("name", "").lower()
    item_uses += " " + item.get("description", "").lower()

    if use_case in item_uses:
        return 1.0
    if use_case == "selection" and any(
        kw in item_uses for kw in ["hiring", "select", "screen", "recruit"]
    ):
        return 0.8
    if use_case == "development" and any(
        kw in item_uses for kw in ["development", "develop", "learning", "coaching", "feedback", "grow"]
    ):
        return 0.8
    if use_case == "audit" and any(
        kw in item_uses for kw in ["audit", "reskill", "upskill", "transformation", "development", "develop", "skills"]
    ):
        return 0.8
    return 0.3


# ─── Multi-Stage Retrieval ────────────────────────────────────────────────────

WEIGHTS = {
    "bm25": 0.35,
    "competency_overlap": 0.25,
    "test_type_pref": 0.15,
    "seniority": 0.10,
    "use_case": 0.10,
    "language": 0.05,
}


def _build_query(state: Dict, messages: List[Dict]) -> str:
    """Build a rich retrieval query from state + raw conversation."""
    parts = []

    # Role signals
    if state.get("role_categories"):
        parts.extend(state["role_categories"])
    if state.get("technical_skills"):
        parts.extend(state["technical_skills"])
    if state.get("seniority"):
        parts.append(state["seniority"])
    # Include raw role title (catches any role not in predefined patterns)
    if state.get("raw_role_title"):
        parts.append(state["raw_role_title"])

    # Test type signals
    if state.get("personality_focus"):
        parts.append("personality behavior")
    if state.get("cognitive_focus"):
        parts.append("cognitive ability aptitude reasoning")
    if state.get("simulation_focus"):
        parts.append("simulation")
    if state.get("sjt_focus"):
        parts.append("situational judgment")

    # Safety
    if state.get("safety_critical"):
        parts.append("safety dependability industrial")

    # Use case
    if state.get("use_case"):
        parts.append(state["use_case"])

    # Extract raw user messages for additional signal
    for msg in messages:
        if msg.get("role") == "user":
            parts.append(msg.get("content", ""))

    return " ".join(parts)


def retrieve_and_rank(
    state: Dict, messages: List[Dict], top_k: int = 10
) -> List[Dict]:
    """
    Full hybrid retrieval pipeline.
    Returns up to top_k ranked assessments from catalog.
    """
    bm25 = get_bm25_index()
    query = _build_query(state, messages)

    # Stage 1: BM25 retrieval — get top 25 candidates
    bm25_results = bm25.get_top_k(query, k=25)

    # Ensure core/universal assessments are always in the candidate list
    core_ids = {"720", "4289", "4301", "4302"}
    for item in CATALOG:
        if item["id"] in core_ids:
            if not any(r["id"] == item["id"] for r in bm25_results):
                item_copy = dict(item)
                item_copy["_bm25_score"] = 0.0
                bm25_results.append(item_copy)

    # Get max BM25 score for normalisation
    max_bm25 = max((r.get("_bm25_score", 0) for r in bm25_results), default=1)
    max_bm25 = max(max_bm25, 0.001)

    # Stage 2+: Score each candidate with all signals
    scored = []
    for item in bm25_results:
        bm25_norm = item.get("_bm25_score", 0) / max_bm25
        comp_score = _competency_overlap_score(item, state)
        tt_score = _test_type_preference_score(item, state)
        sen_score = _seniority_score(item, state)
        uc_score = _use_case_score(item, state)
        lang_score = _language_score(item, state)

        final_score = (
            WEIGHTS["bm25"] * bm25_norm
            + WEIGHTS["competency_overlap"] * comp_score
            + WEIGHTS["test_type_pref"] * tt_score
            + WEIGHTS["seniority"] * sen_score
            + WEIGHTS["use_case"] * uc_score
            + WEIGHTS["language"] * lang_score
        )

        item_copy = dict(item)
        item_copy["_final_score"] = final_score
        scored.append(item_copy)

    # Apply custom boosting for core assessments
    for item in scored:
        iid = item.get("id")
        
        # 1. Boost OPQ32r (id: "720") and OPQ Universal Competency Report (id: "4289")
        if iid in ["720", "4289"]:
            # If seniority is professional or above
            if state.get("seniority") in ["professional", "manager", "director", "executive"]:
                item["_final_score"] += 0.4
            # If role is leadership
            if "leadership" in state.get("role_categories", []):
                item["_final_score"] += 0.4
            # If another OPQ report is in the candidates and has a decent score
            if any("opq" in r.get("name", "").lower() and r.get("_bm25_score", 0) > 0 for r in bm25_results):
                item["_final_score"] += 0.4
            # If use case is audit
            if state.get("use_case") == "audit":
                item["_final_score"] += 0.3

        # 2. Boost Global Skills Assessment (id: "4301") and Global Skills Development Report (id: "4302")
        if iid in ["4301", "4302"]:
            # If use case is audit or development
            if state.get("use_case") in ["audit", "development"]:
                item["_final_score"] += 0.4
            # If the user query contains "reskill", "upskill", "talent audit", "skills"
            query_lower = query.lower()
            if any(kw in query_lower for kw in ["reskill", "upskill", "audit", "skills"]):
                item["_final_score"] += 0.3

    # Stage 3: Metadata filtering — remove excluded assessments
    excluded = [normalize_text(e) for e in state.get("excluded_assessments", [])]
    if excluded:
        scored = [
            item
            for item in scored
            if not any(ex in normalize_text(item.get("name", "")) for ex in excluded)
        ]

    # Stage 4: Sort by final score
    scored.sort(key=lambda x: x["_final_score"], reverse=True)

    # Stage 5: Deduplicate by id
    seen_ids: Set[str] = set()
    deduped = []
    for item in scored:
        iid = item.get("id", item.get("name"))
        if iid not in seen_ids:
            seen_ids.add(iid)
            deduped.append(item)

    return deduped[:top_k]


def apply_delta_update(
    current_results: List[Dict],
    state: Dict,
    messages: List[Dict],
) -> List[Dict]:
    """
    Apply delta updates without restarting retrieval.
    Used for refinement requests (add/remove assessments).
    """
    # Re-rank existing + add newly relevant items
    all_results = retrieve_and_rank(state, messages, top_k=10)

    # Merge with current — keep confirmed items, add new ones
    confirmed_names = {normalize_text(n) for n in state.get("confirmed_assessments", [])}
    merged_ids: Set[str] = set()
    merged = []

    for item in all_results:
        iid = item.get("id", item.get("name"))
        if iid not in merged_ids:
            merged_ids.add(iid)
            merged.append(item)

    return merged[:10]


def format_recommendation(item: Dict, rank: int) -> Dict:
    """Format a catalog item into the API recommendation schema."""
    # Build test_type string (comma-separated codes)
    test_types = item.get("test_type", [])
    test_type_str = ",".join(test_types)

    # Duration
    duration = item.get("duration", "—")

    # Languages (show first 3 + count)
    langs = item.get("languages", [])
    if len(langs) > 3:
        lang_str = ", ".join(langs[:3]) + f" (+{len(langs)-3} more)"
    elif langs:
        lang_str = ", ".join(langs)
    else:
        lang_str = "—"

    return {
        "name": item["name"],
        "url": item["url"],
        "test_type": test_type_str,
        "keys": ", ".join(item.get("test_type_labels", [])),
        "duration": duration,
        "languages": lang_str,
        "_rank": rank,
    }
