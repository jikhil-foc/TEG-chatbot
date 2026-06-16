"""Request/response models for the ask endpoint."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.pipeline.llm.models import Source


class ConversationMessageSchema(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    messages: list[ConversationMessageSchema] = Field(
        default_factory=list,
        description="Prior conversation turns (excluding the current query)",
    )
    session_id: str | None = Field(
        default=None,
        max_length=128,
        description="Client session id for multi-turn clarification state",
    )
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


class AskStreamStatusEvent(BaseModel):
    type: str = "status"
    step: str


class AskStreamTokenEvent(BaseModel):
    type: str = "token"
    content: str


class AskStreamDoneEvent(BaseModel):
    type: str = "done"
    query: str
    answer: str
    language: str | None = None
    sources: list[Source] = Field(default_factory=list)
    clarification: bool = False
    off_topic: bool = False


class AskStreamErrorEvent(BaseModel):
    type: str = "error"
    message: str
