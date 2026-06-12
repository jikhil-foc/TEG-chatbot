"""Hybrid retrieval over the Qdrant collection.

Combines dense (OpenAI) and sparse (BM25) retrieval through Qdrant's built-in
hybrid fusion and returns plain dictionaries in the contract shape:
``{"chunk_id", "score", "content", "metadata"}``.
"""

from __future__ import annotations

import logging

from langchain_core.embeddings import Embeddings
from langchain_qdrant import SparseEmbeddings
from qdrant_client import models as qmodels

from app.pipeline.embedding.config import EmbeddingSettings, get_embedding_settings
from app.pipeline.embedding.dense import build_dense_embeddings
from app.pipeline.embedding.loader import build_breadcrumb
from app.pipeline.embedding.models import SearchResult
from app.pipeline.embedding.qdrant_store import QdrantService
from app.pipeline.embedding.sparse_bm25 import BM25SparseEmbeddings

logger = logging.getLogger(__name__)

# Upper bound on child chunks fetched per parent during expansion.
_MAX_SIBLINGS = 256


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

    def search(
        self,
        query: str,
        top_k: int = 10,
        expand_to_parent: bool = True,
    ) -> list[dict]:
        """Return the ``top_k`` hybrid-search hits for ``query``.

        Each hit is a dict with ``chunk_id``, ``score``, ``content`` and the
        full chunk ``metadata``.

        When ``expand_to_parent`` is true the small matched child chunk is
        replaced by its full parent section (all sibling child chunks sharing
        the same ``parent_chunk_id``, in order). This implements small-to-big
        retrieval: matching stays precise on fine-grained chunks while the LLM
        receives the complete surrounding context (e.g. a matched heading also
        brings along its table). Results are de-duplicated by parent so the same
        section is never returned twice.
        """
        if not query or not query.strip():
            return []

        logger.info(
            "Hybrid search (top_k=%d, expand=%s): %r", top_k, expand_to_parent, query
        )
        hits = self._vector_store.similarity_search_with_score(query, k=top_k)

        results: list[dict] = []
        seen_parents: set[str] = set()
        for document, score in hits:
            metadata = dict(document.metadata)

            if not expand_to_parent:
                results.append(
                    SearchResult(
                        chunk_id=metadata.get("chunk_id", ""),
                        score=float(score),
                        content=document.page_content,
                        metadata=metadata,
                    ).model_dump()
                )
                continue

            parent_id = metadata.get("parent_chunk_id") or metadata.get("chunk_id", "")
            if parent_id in seen_parents:
                continue
            seen_parents.add(parent_id)

            content = self._build_parent_content(parent_id, metadata)
            results.append(
                SearchResult(
                    chunk_id=metadata.get("chunk_id", ""),
                    score=float(score),
                    content=content,
                    metadata=metadata,
                ).model_dump()
            )
        return results

    def _build_parent_content(self, parent_id: str, hit_metadata: dict) -> str:
        """Reassemble a parent section from its child chunks, ordered in document.

        Falls back to the matched chunk's own text if no siblings are found.
        """
        siblings = self._fetch_siblings(parent_id)
        blocks = [
            (md.get("raw_content") or "").strip()
            for md in sorted(siblings, key=lambda md: md.get("chunk_index", 0))
            if (md.get("raw_content") or "").strip()
        ]
        if not blocks:
            fallback = (hit_metadata.get("raw_content") or "").strip()
            blocks = [fallback] if fallback else []

        body = "\n\n".join(blocks)
        breadcrumb = build_breadcrumb(
            hit_metadata.get("title", ""),
            hit_metadata.get("header_path", []) or [],
        )
        if breadcrumb and body:
            return f"{breadcrumb}\n\n{body}"
        return body or breadcrumb

    def _fetch_siblings(self, parent_id: str) -> list[dict]:
        """Fetch the metadata of every child chunk sharing ``parent_chunk_id``."""
        if not parent_id:
            return []

        scroll_filter = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="metadata.parent_chunk_id",
                    match=qmodels.MatchValue(value=parent_id),
                )
            ]
        )

        collected: list[dict] = []
        offset = None
        client = self._service.client
        while True:
            points, offset = client.scroll(
                collection_name=self._settings.collection_name,
                scroll_filter=scroll_filter,
                limit=128,
                with_payload=True,
                with_vectors=False,
                offset=offset,
            )
            for point in points:
                payload = point.payload or {}
                metadata = payload.get("metadata") or {}
                collected.append(metadata)
            if offset is None or len(collected) >= _MAX_SIBLINGS:
                break
        return collected
