"""
FastAPI Application — SHL Assessment Recommender
Endpoints:
  GET  /health
  POST /chat

SCHEMA (non-negotiable per assignment spec):
  Response:
    reply: str
    recommendations: List[Recommendation]   ← empty [] when gathering/refusing, NOT null
    end_of_conversation: bool
"""
import os
import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from app.agent import run_agent

# ─── App Setup ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="SHL Assessment Recommender",
    description=(
        "Conversational agent for recommending SHL Individual Test Solutions. "
        "Optimised for Recall@10, schema compliance, and robustness."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Schemas ──────────────────────────────────────────────────────────────────


class Message(BaseModel):
    role: str
    content: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("user", "assistant"):
            raise ValueError("role must be 'user' or 'assistant'")
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("content must not be empty")
        return v.strip()


class ChatRequest(BaseModel):
    messages: List[Message]

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, v: List[Message]) -> List[Message]:
        if not v:
            raise ValueError("messages must not be empty")
        if v[-1].role != "user":
            raise ValueError("last message must be from the user")
        return v


class Recommendation(BaseModel):
    name: str
    url: str
    test_type: str


class ChatResponse(BaseModel):
    """
    Non-negotiable response schema per SHL assignment specification.
    - reply: the agent's text response
    - recommendations: EMPTY [] when clarifying/refusing, 1–10 items when committed
    - end_of_conversation: true only when agent considers task complete
    """
    reply: str
    recommendations: List[Recommendation]  # Always a list, never null
    end_of_conversation: bool


# ─── Endpoints ────────────────────────────────────────────────────────────────


@app.get("/health", tags=["health"])
async def health_check() -> Dict[str, Any]:
    """Health check endpoint. Returns {"status": "ok"} with HTTP 200."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Main stateless chat endpoint.

    Accepts the full conversation history on every call.
    Returns:
      - reply: agent's next message
      - recommendations: [] when clarifying, 1-10 SHL catalog items when ready
      - end_of_conversation: true when task is complete
    """
    messages = [m.model_dump() for m in request.messages]

    try:
        reply_text, recs, end_of_conv = run_agent(messages)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(exc)}",
        )

    # Build validated recommendations — always return a list (never null)
    validated_recs: List[Recommendation] = []
    if recs:
        for rec in recs:
            try:
                validated_recs.append(
                    Recommendation(
                        name=rec.get("name", ""),
                        url=rec.get("url", ""),
                        test_type=rec.get("test_type", ""),
                    )
                )
            except Exception:
                pass  # Skip any malformed items

    return ChatResponse(
        reply=reply_text,
        recommendations=validated_recs,
        end_of_conversation=end_of_conv,
    )


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
