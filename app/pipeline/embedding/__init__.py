"""Hybrid (dense + sparse) RAG indexing and retrieval package.

Indexes pre-chunked JSON documents into Qdrant using OpenAI dense embeddings
(`text-embedding-3-large`) and a rank-bm25 sparse encoder, and exposes a hybrid
retriever. See :mod:`app.pipeline.embedding.orchestrator` for the indexing/search
entry points (the CLI lives in ``scripts/embedding.py``).
"""

from app.pipeline.embedding.config import EmbeddingSettings, get_embedding_settings
from app.pipeline.embedding.models import IndexSummary, SearchResult
from app.pipeline.embedding.orchestrator import run_indexing, run_search

__all__ = [
    "EmbeddingSettings",
    "get_embedding_settings",
    "IndexSummary",
    "SearchResult",
    "run_indexing",
    "run_search",
]
