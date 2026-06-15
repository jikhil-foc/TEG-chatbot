"""Service orchestration for the end-to-end ingestion pipeline."""

from __future__ import annotations

from app.pipeline.embedding.cache import invalidate_retriever
from app.pipeline.ingestion import IngestionConfig, IngestionResult, run_ingestion_pipeline


def ingest(config: IngestionConfig) -> IngestionResult:
    """Run crawl -> language -> chunk -> index and refresh the cached retriever.

    Synchronous and long-running; call from a worker thread in async routes.
    """
    result = run_ingestion_pipeline(config)
    invalidate_retriever()
    return result
