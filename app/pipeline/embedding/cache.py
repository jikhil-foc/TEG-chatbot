"""Shared retriever cache used by API routes after (re)indexing."""

from __future__ import annotations

from app.pipeline.embedding.retriever import HybridRetriever

_retriever: HybridRetriever | None = None


def get_retriever() -> HybridRetriever:
    """Lazily build and cache the hybrid retriever across requests."""
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever.from_settings()
    return _retriever


def invalidate_retriever() -> None:
    """Drop the cached retriever so the next request rebuilds from disk/Qdrant."""
    global _retriever
    _retriever = None
