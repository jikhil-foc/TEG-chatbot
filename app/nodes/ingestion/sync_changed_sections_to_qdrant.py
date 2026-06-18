"""Sync changed sections to Qdrant LangGraph node."""

from __future__ import annotations

import json

from app.graphs.ingest_state import IngestionState
from app.pipelines.ingestion.content_change_report import ContentChangeReport
from app.pipelines.ingestion.page_section import PageSection
from app.pipelines.ingestion.sync_changed_sections_job import sync_changed_sections_to_qdrant


def _load_change_report(state: IngestionState) -> ContentChangeReport:
    payload = json.loads(state.get("change_report_json", "{}"))
    changed_sections = [
        PageSection(
            url=section["url"],
            title=section["title"],
            language=section.get("language"),
            content_type=section["content_type"],
            header_path=section.get("header_path", []),
            section_key=section["section_key"],
            section_id=section["section_id"],
            content=section["content"],
            content_hash=section["content_hash"],
        )
        for section in payload.get("changed_sections", [])
    ]
    return ContentChangeReport(
        unchanged_section_ids=payload.get("unchanged_section_ids", []),
        changed_sections=changed_sections,
        removed_section_ids=payload.get("removed_section_ids", []),
        removed_chunk_ids=payload.get("removed_chunk_ids", []),
    )


def sync_changed_sections_node(state: IngestionState) -> dict:
    """Delete stale vectors, update registry rows, and run incremental indexing."""
    change_report = _load_change_report(state)
    result = sync_changed_sections_to_qdrant(change_report)

    steps = list(state.get("steps_completed", []))
    steps.append("sync_changed_sections_to_qdrant")

    return {
        **result,
        "steps_completed": steps,
    }
