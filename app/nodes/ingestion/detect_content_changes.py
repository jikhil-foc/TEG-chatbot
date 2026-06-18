"""Detect content changes LangGraph node."""

from __future__ import annotations

import json
from pathlib import Path

from app.db.database_session import session_scope
from app.graphs.ingest_state import IngestionState
from app.pipelines.ingestion.content_change_detector import detect_content_changes
from app.pipelines.ingestion.langchain_page_chunker import load


def detect_content_changes_node(state: IngestionState) -> dict:
    """Compare crawled pages against PostgreSQL and record change counts."""
    input_path = Path(state["crawled_file"])
    pages = load(input_path)

    with session_scope() as session:
        change_report = detect_content_changes(pages, session)

    steps = list(state.get("steps_completed", []))
    steps.append("detect_content_changes")

    serialised_report = {
        "unchanged_section_ids": change_report.unchanged_section_ids,
        "changed_sections": [
            {
                "url": section.url,
                "title": section.title,
                "language": section.language,
                "content_type": section.content_type,
                "header_path": section.header_path,
                "section_key": section.section_key,
                "section_id": section.section_id,
                "content": section.content,
                "content_hash": section.content_hash,
            }
            for section in change_report.changed_sections
        ],
        "removed_section_ids": change_report.removed_section_ids,
        "removed_chunk_ids": change_report.removed_chunk_ids,
    }

    return {
        "change_report_json": json.dumps(serialised_report, ensure_ascii=False),
        "change_unchanged_sections": len(change_report.unchanged_section_ids),
        "change_changed_sections": len(change_report.changed_sections),
        "change_removed_sections": len(change_report.removed_section_ids),
        "change_removed_chunks": len(change_report.removed_chunk_ids),
        "steps_completed": steps,
    }
