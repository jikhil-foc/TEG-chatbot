"""Sync changed sections to Qdrant after content change detection."""

from __future__ import annotations

import logging
import uuid

from app.config.embedding_settings import get_embedding_settings
from app.db.content_registry_repository import ContentRegistryRepository
from app.db.database_session import session_scope
from app.pipelines.ingestion.content_change_report import ContentChangeReport
from app.pipelines.ingestion.incremental_indexing_job import run_incremental_indexing
from app.pipelines.ingestion.langchain_page_chunker import chunk_page_section
from app.services.bm25_encoder import BM25SparseEmbeddings
from app.services.openai_embeddings import build_dense_embeddings
from app.services.qdrant_vector_store import QdrantService

logger = logging.getLogger(__name__)


def sync_changed_sections_to_qdrant(change_report: ContentChangeReport) -> dict:
    """Delete stale vectors, update the registry, and run incremental indexing."""
    settings = get_embedding_settings()

    removed_ids = list(dict.fromkeys(change_report.removed_chunk_ids))
    changed_sections = change_report.changed_sections

    if not change_report.has_changes:
        logger.info("No content changes detected; skipping Qdrant sync")
        return {
            "index_collection_name": settings.collection_name,
            "index_total_documents": 0,
            "index_uploaded": 0,
            "index_batches": 0,
            "index_recreated_collection": False,
            "index_dense_embeddings_generated": 0,
            "change_unchanged_sections": len(change_report.unchanged_section_ids),
            "change_changed_sections": 0,
            "change_removed_sections": len(change_report.removed_section_ids),
            "change_removed_chunks": len(removed_ids),
            "change_changed_chunks": 0,
        }

    try:
        sparse = BM25SparseEmbeddings.load(settings.bm25_state_path)
    except FileNotFoundError:
        sparse = BM25SparseEmbeddings(
            vocab={"__bootstrap__": 0},
            idf={"__bootstrap__": 0.0},
            avgdl=1.0,
        )
    dense = build_dense_embeddings(settings)
    qdrant_service = QdrantService(
        settings=settings,
        dense_embeddings=dense,
        sparse_embeddings=sparse,
    )
    qdrant_service.ensure_collection(recreate=False)
    qdrant_service.ensure_section_id_index()

    if removed_ids:
        qdrant_service.delete_points_by_chunk_ids(removed_ids)

    with session_scope() as session:
        repository = ContentRegistryRepository(session)
        for section in changed_sections:
            section_chunks, _ = chunk_page_section(section)
            change_report.changed_chunks.extend(section_chunks)
            repository.replace_section_chunks(uuid.UUID(section.section_id), section_chunks)

    index_summary = run_incremental_indexing(change_report, settings=settings)

    return {
        "index_collection_name": index_summary.collection_name,
        "index_total_documents": index_summary.total_documents,
        "index_uploaded": index_summary.uploaded,
        "index_batches": index_summary.batches,
        "index_recreated_collection": index_summary.recreated_collection,
        "index_dense_embeddings_generated": index_summary.dense_embeddings_generated,
        "change_unchanged_sections": len(change_report.unchanged_section_ids),
        "change_changed_sections": len(change_report.changed_sections),
        "change_removed_sections": len(change_report.removed_section_ids),
        "change_removed_chunks": len(removed_ids),
        "change_changed_chunks": len(change_report.changed_chunks),
    }
