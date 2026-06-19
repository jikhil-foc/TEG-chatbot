"""Populate content registry after baseline indexing."""

from __future__ import annotations

import logging
from pathlib import Path

from app.db.content_registry_repository import get_content_registry_counts
from app.db.database_session import session_scope
from app.graphs.ingest_state import IngestionState
from app.pipelines.ingestion.langchain_page_chunker import OUTPUT_PATH
from app.pipelines.ingestion.populate_content_registry import (
    populate_content_registry_from_baseline,
)

logger = logging.getLogger(__name__)


def populate_content_registry_node(state: IngestionState) -> dict:
    """Seed PostgreSQL tables from crawl/chunk JSON after a baseline ingest."""
    crawled_file = Path(state["crawled_file"])
    chunked_file = Path(state.get("chunked_file") or OUTPUT_PATH)
    populate_content_registry_from_baseline(crawled_file, chunked_file)

    with session_scope() as session:
        registry = get_content_registry_counts(session)

    logger.info(
        "Content registry populated: pages=%d sections=%d chunks=%d",
        registry["pages"],
        registry["sections"],
        registry["chunks"],
    )

    steps = list(state.get("steps_completed", []))
    steps.append("populate_content_registry")
    return {
        "steps_completed": steps,
        "registry_pages": registry["pages"],
        "registry_sections": registry["sections"],
        "registry_chunks": registry["chunks"],
    }
