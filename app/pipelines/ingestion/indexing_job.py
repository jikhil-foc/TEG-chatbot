"""Hybrid RAG indexing pipeline orchestrator.

Indexes pre-chunked JSON into Qdrant using OpenAI dense embeddings
(``text-embedding-3-large``) and a rank-bm25 sparse encoder, enabling hybrid
(dense + sparse) retrieval.

The command-line interface lives in ``scripts/embedding.py``; this module only
exposes the reusable :func:`run_indexing` and :func:`run_search` functions.

Requires ``OPENAI_API_KEY`` in the environment/.env and a reachable Qdrant
instance (defaults to ``http://localhost:6333``).
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.config.embedding_settings import EmbeddingSettings, get_embedding_settings
from app.services.openai_embeddings import build_dense_embeddings
from app.pipelines.retrieval.chunk_loader import load_documents
from app.models.embedding import IndexSummary
from app.services.qdrant_vector_store import QdrantService
from app.pipelines.retrieval.hybrid_retriever import HybridRetriever
from app.services.bm25_encoder import BM25SparseEmbeddings

logger = logging.getLogger(__name__)


def run_indexing(
    settings: EmbeddingSettings | None = None,
    input_path: Path | None = None,
    recreate: bool = False,
) -> IndexSummary:
    """Run the full indexing pipeline and return an :class:`IndexSummary`.

    Steps: load chunks -> fit + persist BM25 -> ensure collection -> batch
    upload dense + sparse vectors with metadata.
    """
    settings = settings or get_embedding_settings()
    input_path = input_path or settings.input_path

    documents = load_documents(input_path, settings.token_encoding)
    if not documents:
        raise ValueError(f"No indexable documents found in {input_path}")

    logger.info("Fitting BM25 sparse encoder on %d documents", len(documents))
    sparse = BM25SparseEmbeddings.fit(
        corpus=[doc.page_content for doc in documents],
        k1=settings.bm25_k1,
        b=settings.bm25_b,
    )
    sparse.save(settings.bm25_state_path)

    dense = build_dense_embeddings(settings)

    service = QdrantService(
        settings=settings,
        dense_embeddings=dense,
        sparse_embeddings=sparse,
    )
    recreated = service.ensure_collection(recreate=recreate)
    vector_store = service.build_vector_store()
    uploaded, batches = service.upload_documents(vector_store, documents)

    summary = IndexSummary(
        collection_name=settings.collection_name,
        total_documents=len(documents),
        uploaded=uploaded,
        batches=batches,
        recreated_collection=recreated,
    )
    logger.info("Indexing complete: %s", summary.model_dump())
    return summary


def run_search(
    query: str,
    top_k: int = 10,
    settings: EmbeddingSettings | None = None,
    expand_to_parent: bool = True,
) -> list[dict]:
    """Convenience wrapper that builds a retriever and runs one search."""
    retriever = HybridRetriever.from_settings(settings)
    return retriever.search(query, top_k=top_k, expand_to_parent=expand_to_parent)
