"""Hybrid retrieval over the Qdrant collection.

Combines dense (OpenAI) and sparse (BM25) retrieval through Qdrant's built-in
hybrid fusion and returns plain dictionaries in the contract shape:
``{"chunk_id", "score", "content", "metadata"}``.
"""

from __future__ import annotations

import logging

from langchain_core.embeddings import Embeddings
from langchain_qdrant import SparseEmbeddings

from app.pipeline.embedding.config import EmbeddingSettings, get_embedding_settings
from app.pipeline.embedding.dense import build_dense_embeddings
from app.pipeline.embedding.models import SearchResult
from app.pipeline.embedding.qdrant_store import QdrantService
from app.pipeline.embedding.sparse_bm25 import BM25SparseEmbeddings

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Run hybrid dense + sparse search against an indexed Qdrant collection."""

    def __init__(
        self,
        settings: EmbeddingSettings,
        dense_embeddings: Embeddings,
        sparse_embeddings: SparseEmbeddings,
    ) -> None:
        self._settings = settings
        self._service = QdrantService(
            settings=settings,
            dense_embeddings=dense_embeddings,
            sparse_embeddings=sparse_embeddings,
        )
        self._vector_store = self._service.build_vector_store()

    @classmethod
    def from_settings(
        cls,
        settings: EmbeddingSettings | None = None,
    ) -> "HybridRetriever":
        """Build a retriever, loading the persisted BM25 state from disk."""
        settings = settings or get_embedding_settings()
        dense = build_dense_embeddings(settings)
        sparse = BM25SparseEmbeddings.load(settings.bm25_state_path)
        return cls(settings=settings, dense_embeddings=dense, sparse_embeddings=sparse)

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """Return the ``top_k`` hybrid-search hits for ``query``.

        Each hit is a dict with ``chunk_id``, ``score``, ``content`` and the
        full chunk ``metadata``.
        """
        if not query or not query.strip():
            return []

        logger.info("Hybrid search (top_k=%d): %r", top_k, query)
        hits = self._vector_store.similarity_search_with_score(query, k=top_k)

        results: list[dict] = []
        for document, score in hits:
            metadata = dict(document.metadata)
            results.append(
                SearchResult(
                    chunk_id=metadata.get("chunk_id", ""),
                    score=float(score),
                    content=document.page_content,
                    metadata=metadata,
                ).model_dump()
            )
        return results
