"""TEG ingestion application facade."""

from __future__ import annotations

from app.graphs.teg_ingest_graph import run_ingestion_pipeline
from app.models.ingest_request import IngestionConfig, IngestionResult
from app.pipelines.retrieval.retriever_cache import invalidate_retriever


def ingest(config: IngestionConfig) -> IngestionResult:
    result = run_ingestion_pipeline(config)
    invalidate_retriever()
    return result
