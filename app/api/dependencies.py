"""Shared FastAPI dependencies."""

from __future__ import annotations

from app.pipelines.retrieval.hybrid_retriever import HybridRetriever
from app.pipelines.retrieval.retriever_cache import get_retriever as _get_retriever


def get_retriever() -> HybridRetriever:
    """FastAPI dependency returning the cached hybrid retriever."""
    return _get_retriever()
