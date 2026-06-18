"""Incremental hybrid indexing for changed sections only."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.documents import Document
from qdrant_client import models

from app.config.embedding_settings import EmbeddingSettings, get_embedding_settings
from app.db.content_registry_repository import ContentRegistryRepository
from app.db.database_session import session_scope
from app.models.embedding import IndexSummary
from app.pipelines.ingestion.content_change_report import ContentChangeReport
from app.pipelines.retrieval.chunk_loader import child_chunks_to_documents
from app.services.bm25_encoder import BM25SparseEmbeddings
from app.services.openai_embeddings import build_dense_embeddings
from app.services.qdrant_vector_store import QdrantService

logger = logging.getLogger(__name__)


def _build_page_content(document: Document) -> str:
    return document.page_content


def _build_payload(document: Document) -> dict[str, Any]:
    metadata = dict(document.metadata)
    return {
        "page_content": document.page_content,
        "metadata": metadata,
    }


def _retrieve_dense_vectors(
    service: QdrantService,
    chunk_ids: list[str],
) -> dict[str, list[float]]:
    if not chunk_ids:
        return {}
    dense_name = service._settings.dense_vector_name  # noqa: SLF001
    records = service.client.retrieve(
        collection_name=service._settings.collection_name,  # noqa: SLF001
        ids=chunk_ids,
        with_vectors=[dense_name],
    )
    vectors: dict[str, list[float]] = {}
    for record in records:
        vector = record.vector
        if isinstance(vector, dict):
            dense = vector.get(dense_name)
            if dense is not None:
                vectors[str(record.id)] = list(dense)
    return vectors


def _upsert_hybrid_points(
    service: QdrantService,
    documents: list[Document],
    dense_vectors: dict[str, list[float]],
    sparse_encoder: BM25SparseEmbeddings,
    batch_size: int,
) -> tuple[int, int]:
    dense_name = service._settings.dense_vector_name  # noqa: SLF001
    sparse_name = service._settings.sparse_vector_name  # noqa: SLF001
    collection_name = service._settings.collection_name  # noqa: SLF001

    uploaded = 0
    batches = 0
    for start in range(0, len(documents), batch_size):
        batch = documents[start : start + batch_size]
        points: list[models.PointStruct] = []
        sparse_vectors = sparse_encoder.embed_documents(
            [_build_page_content(document) for document in batch]
        )
        for document, sparse_vector in zip(batch, sparse_vectors, strict=True):
            chunk_id = document.metadata["chunk_id"]
            dense_vector = dense_vectors[chunk_id]
            points.append(
                models.PointStruct(
                    id=chunk_id,
                    vector={
                        dense_name: dense_vector,
                        sparse_name: models.SparseVector(
                            indices=sparse_vector.indices,
                            values=sparse_vector.values,
                        ),
                    },
                    payload=_build_payload(document),
                )
            )
        service.client.upsert(collection_name=collection_name, points=points)
        uploaded += len(points)
        batches += 1
    return uploaded, batches


def run_incremental_indexing(
    change_report: ContentChangeReport,
    settings: EmbeddingSettings | None = None,
) -> IndexSummary:
    """Refit BM25 on the full corpus and update only changed dense embeddings."""
    settings = settings or get_embedding_settings()

    with session_scope() as session:
        repository = ContentRegistryRepository(session)
        all_chunks = repository.load_child_chunks_from_registry()

    if not all_chunks:
        raise ValueError("No chunks found in the content registry for incremental indexing")

    documents = child_chunks_to_documents(all_chunks, settings.token_encoding)
    if not documents:
        raise ValueError("No indexable documents found in the content registry")

    logger.info("Fitting BM25 sparse encoder on %d documents", len(documents))
    sparse = BM25SparseEmbeddings.fit(
        corpus=[document.page_content for document in documents],
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
    recreated = service.ensure_collection(recreate=False)
    service.ensure_section_id_index()

    changed_chunk_ids = {chunk.chunk_id for chunk in change_report.changed_chunks}
    changed_documents = [
        document
        for document in documents
        if document.metadata["chunk_id"] in changed_chunk_ids
    ]
    unchanged_documents = [
        document
        for document in documents
        if document.metadata["chunk_id"] not in changed_chunk_ids
    ]

    dense_vectors: dict[str, list[float]] = {}
    if changed_documents:
        logger.info("Generating dense embeddings for %d changed chunks", len(changed_documents))
        changed_texts = [document.page_content for document in changed_documents]
        changed_dense = dense.embed_documents(changed_texts)
        for document, vector in zip(changed_documents, changed_dense, strict=True):
            dense_vectors[document.metadata["chunk_id"]] = vector

    if unchanged_documents:
        logger.info(
            "Reusing dense embeddings for %d unchanged chunks",
            len(unchanged_documents),
        )
        unchanged_ids = [document.metadata["chunk_id"] for document in unchanged_documents]
        dense_vectors.update(_retrieve_dense_vectors(service, unchanged_ids))

    missing_ids = [
        document.metadata["chunk_id"]
        for document in documents
        if document.metadata["chunk_id"] not in dense_vectors
    ]
    if missing_ids:
        logger.info(
            "Generating dense embeddings for %d new chunks without prior vectors",
            len(missing_ids),
        )
        missing_documents = [
            document
            for document in documents
            if document.metadata["chunk_id"] in missing_ids
        ]
        missing_dense = dense.embed_documents(
            [document.page_content for document in missing_documents]
        )
        for document, vector in zip(missing_documents, missing_dense, strict=True):
            dense_vectors[document.metadata["chunk_id"]] = vector

    uploaded, batches = _upsert_hybrid_points(
        service=service,
        documents=documents,
        dense_vectors=dense_vectors,
        sparse_encoder=sparse,
        batch_size=settings.upload_batch_size,
    )

    summary = IndexSummary(
        collection_name=settings.collection_name,
        total_documents=len(documents),
        uploaded=uploaded,
        batches=batches,
        recreated_collection=recreated,
        dense_embeddings_generated=len(changed_chunk_ids) + len(missing_ids),
    )
    logger.info("Incremental indexing complete: %s", summary.model_dump())
    return summary
