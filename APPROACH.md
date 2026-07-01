<style>
  body { font-size: 11px; line-height: 1.3; }
  h1 { font-size: 16px; margin-top: 8px; margin-bottom: 4px; }
  h2 { font-size: 13px; margin-top: 8px; margin-bottom: 4px; }
  p, ul { margin-top: 4px; margin-bottom: 4px; }
  pre, code { font-size: 10px; }
</style>

# Approach Document

## 1. Architecture

The system is a conversational retrieval agent separating deterministic retrieval from LLM generation.

```text
[User POST] ──> [State Extractor] ──> [Intent Detection] ──> [BM25 Search & Meta-Scoring] ──> [LLM Generation] ──> [Validation]
```

## 2. Retrieval Design

**Hybrid retrieval pipeline to maximise Recall@10:**
- **Stage 1 (BM25):** Over a composite field (name + desc + competencies + use_cases). Catches exact keyword signals ("Java", "Docker", "HIPAA").
- **Stage 2 (Metadata Scoring):** Blends BM25 (35%) with Competency overlap (25%), Test type (15%), Seniority (10%), Use-case (10%), Language (5%).
- **Stage 3 (LLM reranking):** Groq Llama 3.3 70b receives the top-10 candidates, selects optimal items, and writes rationale.
- **Stage 4 (Validation):** Every URL outputted is checked against the catalog. Hallucinated items are dropped.
- *Why not pure embeddings?* BM25 outperforms embeddings for exact-match technical skills. Embeddings add noise for short domain terms.

## 3. State Reconstruction & Clarification

Every API call parses the full history to build a deterministic state object (Role, Seniority, Skills, Use-case, Turn Count). No session memory equals no state-sync bugs.
- **Turn budget:** Max 8 turns.
- **Clarification Policy:** Ask only when role AND seniority are unknown. If `turn_count >= 6`, recommend immediately. Use compound questions to prevent wasting turns.

## 4. Evaluation Methodology

Automated test suite with >40 tests measuring Recall, Groundedness, and Safety.
- **Recall@10 target (≥0.7):** Tested against 10 ground-truth HR conversation scenarios.
- **Behavior Probes & Schema Checks:** Ensure 100% schema compliance, zero hallucinations, and proper refusal of legal/compensation queries.

## 5. Tradeoffs & Failed Experiments
- **Failed: Pure semantic search** — Poor recall for exact technical terms. Dropped.
- **Failed: Full catalog prompt** — Too slow and expensive (30k tokens/call). Switched to RAG.
- **Tradeoff: Groq Llama 3.3 70b** — Extremely fast and strictly follows markdown table instructions.
- **Tradeoff: In-memory BM25** — Sufficient and instant for a 60-item catalog, avoiding external vector-DB overhead.


