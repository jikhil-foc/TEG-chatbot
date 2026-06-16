"""Pydantic models for the LLM question-answering pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Source(BaseModel):
    """A reranked retrieval hit cited in the generated answer."""

    chunk_id: str
    url: str = ""
    title: str = ""
    score: float = Field(
        default=0.0, description="Original hybrid-search score from retrieval"
    )
    rerank_score: float = Field(
        default=0.0, description="Cohere relevance score from reranking"
    )


class AnswerResult(BaseModel):
    """The grounded answer and the sources it was derived from."""

    answer: str
    language: str | None = Field(
        default=None, description="Detected query language the answer replies in"
    )
    sources: list[Source] = Field(default_factory=list)
