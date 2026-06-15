"""Request/response models for the ask endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.pipeline.llm.models import Source


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    top_k: int = Field(
        default=10, ge=1, le=100, description="Hybrid-search hits to retrieve"
    )
    rerank_top_n: int = Field(
        default=5, ge=1, le=50, description="Reranked hits to keep as context"
    )


class AskResponse(BaseModel):
    query: str
    answer: str
    language: str | None = Field(
        default=None, description="Detected query language the answer replies in"
    )
    sources: list[Source]
