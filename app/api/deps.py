"""Shared FastAPI dependencies."""

from __future__ import annotations

from app.pipeline.embedding.cache import get_retriever as _get_retriever
from app.pipeline.embedding.retriever import HybridRetriever


def get_retriever() -> HybridRetriever:
    """FastAPI dependency returning the cached hybrid retriever.

    Building the retriever loads the BM25 state from disk and connects to
    Qdrant; FastAPI runs this sync dependency in a worker thread automatically.
    Raises ``FileNotFoundError`` when the index has not been built yet.
    """
    return _get_retriever()
