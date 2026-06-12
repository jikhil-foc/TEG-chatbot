"""Hybrid (dense + sparse) RAG indexing and retrieval package.

Indexes pre-chunked JSON documents into Qdrant using OpenAI dense embeddings
(`text-embedding-3-large`) and a rank-bm25 sparse encoder, and exposes a hybrid
retriever. See :mod:`app.pipeline.embedding_pipeline` for the orchestrator/CLI.
"""

from app.pipeline.embedding.config import EmbeddingSettings, get_embedding_settings
from app.pipeline.embedding.models import IndexSummary, SearchResult

__all__ = [
    "EmbeddingSettings",
    "get_embedding_settings",
    "IndexSummary",
    "SearchResult",
]
