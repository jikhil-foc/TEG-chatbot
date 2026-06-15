"""Typed state for the LangGraph question-answering workflow."""

from __future__ import annotations

from typing import Any, TypedDict

from app.pipeline.embedding.config import EmbeddingSettings
from app.pipeline.embedding.retriever import HybridRetriever
from app.pipeline.llm.models import Source


class QAState(TypedDict, total=False):
    """Mutable state passed between QA graph nodes."""

    # Request parameters and shared dependencies.
    query: str
    top_k: int
    rerank_top_n: int
    retriever: HybridRetriever
    settings: EmbeddingSettings
    max_retries: int

    # Detect-language outputs.
    language: str

    # Retrieval / rerank outputs.
    hits: list[dict[str, Any]]
    reranked: list[dict[str, Any]]

    # Answer / citation outputs.
    answer: str
    sources: list[Source]

    # Control flow.
    fallback: bool
    validation_passed: bool
    retry_count: int

    # Progress tracking.
    steps_completed: list[str]
