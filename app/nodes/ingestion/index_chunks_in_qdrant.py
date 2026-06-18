"""Index chunks in Qdrant ingestion node."""

from __future__ import annotations

from pathlib import Path

from app.config.embedding_settings import get_embedding_settings
from app.graphs.ingest_state import IngestionState
from app.pipelines.ingestion.indexing_job import run_indexing
from app.pipelines.ingestion.langchain_page_chunker import OUTPUT_PATH


def embed_to_qdrant_node(state: IngestionState) -> dict:
    settings = get_embedding_settings()
    input_path = Path(state["chunked_file"]) if state.get("chunked_file") else OUTPUT_PATH
    index_summary = run_indexing(
        settings=settings,
        input_path=input_path,
        recreate=state.get("recreate", False),
    )

    steps = list(state.get("steps_completed", []))
    steps.append("embed_to_qdrant")

    return {
        "index_collection_name": index_summary.collection_name,
        "index_total_documents": index_summary.total_documents,
        "index_uploaded": index_summary.uploaded,
        "index_batches": index_summary.batches,
        "index_recreated_collection": index_summary.recreated_collection,
        "steps_completed": steps,
    }
