"""Populate content registry after baseline indexing."""

from __future__ import annotations

from pathlib import Path

from app.graphs.ingest_state import IngestionState
from app.pipelines.ingestion.langchain_page_chunker import OUTPUT_PATH
from app.pipelines.ingestion.populate_content_registry import (
    populate_content_registry_from_baseline,
)


def populate_content_registry_node(state: IngestionState) -> dict:
    """Seed PostgreSQL tables from crawl/chunk JSON after a baseline ingest."""
    crawled_file = Path(state["crawled_file"])
    chunked_file = Path(state.get("chunked_file") or OUTPUT_PATH)
    populate_content_registry_from_baseline(crawled_file, chunked_file)

    steps = list(state.get("steps_completed", []))
    steps.append("populate_content_registry")
    return {"steps_completed": steps}
