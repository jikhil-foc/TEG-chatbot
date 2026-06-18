"""Shared retriever cache used by API routes after (re)indexing."""

from __future__ import annotations

from app.pipelines.retrieval.hybrid_retriever import HybridRetriever

_retriever: HybridRetriever | None = None


def get_retriever() -> HybridRetriever:
    """Lazily build and cache the hybrid retriever across requests.

    The retriever loads BM25 state from disk at construction time, so callers
    must call :func:`invalidate_retriever` after re-indexing to pick up changes.
    """
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever.from_settings()
    return _retriever


def invalidate_retriever() -> None:
    """Drop the cached retriever after indexing or BM25 state changes.

    The next :func:`get_retriever` call rebuilds from the persisted BM25 file
    and reconnects to Qdrant with the current collection contents.
    """
    global _retriever
    _retriever = None
