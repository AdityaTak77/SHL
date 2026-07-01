# SHL Assessment Recommender

A production-ready conversational AI system for recommending SHL Individual Test Solutions. Built to maximise **Recall@10**, pass all schema checks, and handle real hiring scenarios end-to-end.

## Architecture Overview

```
POST /chat → Agent → State Extraction → BM25 + Metadata Retrieval → LLM Ranking → Validation → Response
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| BM25 keyword retrieval | Catches exact technology/skill matches (Java, Docker) |
| Metadata scoring | Ensures seniority, language, and use-case alignment |
| Gemini 2.0 Flash | Fast, cost-effective, strong instruction following |
| Hallucination guard | Assert URL in catalog before every response |
| Stateless + full history | Simple, robust, no session state bugs |
| Compound clarification | Preserves turns (8-turn budget) |

## Quick Start

```bash
# 1. Set your API key
cp .env.example .env
# Edit .env and add GEMINI_API_KEY

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 4. Test health
curl http://localhost:8000/health
```

## API Usage

### POST /chat

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "I need to hire senior Java developers"}
    ]
  }'
```

#### Request Schema
```json
{
  "messages": [
    {"role": "user" | "assistant", "content": "string"}
  ]
}
```

- Full conversation history is sent on every request (stateless design)
- Last message must be from "user"

#### Response Schema
```json
{
  "message": "string",
  "recommendations": [
    {
      "name": "Assessment Name",
      "url": "https://www.shl.com/products/product-catalog/view/...",
      "test_type": "A,K,P"
    }
  ] | null,
  "end_of_conversation": false
}
```

- `recommendations`: null when clarifying, comparing, or refusing; 1-10 items when recommending
- `test_type`: comma-separated codes (A=Ability, B=Biodata, C=Competencies, D=Development, K=Knowledge, P=Personality, S=Simulations)

## Running Tests

```bash
pytest tests/ -v
```

## Docker Deployment

```bash
docker build -t shl-recommender .
docker run -p 8000:8000 -e GEMINI_API_KEY=your_key shl-recommender
```

## Project Structure

```
SHL/
├── app/
│   ├── main.py          # FastAPI app, /health, /chat
│   ├── agent.py         # Core agent orchestration
│   ├── retrieval.py     # BM25 + metadata scoring engine
│   ├── state.py         # State reconstruction from history
│   ├── prompts.py       # Prompt templates + refusal logic
│   └── catalog.py       # Catalog loading + validation
├── catalog/
│   └── shl_catalog.json # Full SHL Individual Test Solutions catalog
├── tests/
│   └── test_recommender.py  # 40+ tests
├── requirements.txt
├── Dockerfile
└── README.md
```
