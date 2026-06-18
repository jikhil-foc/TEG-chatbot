"""Enrich crawled pages with language tags."""

from __future__ import annotations

from pathlib import Path

from app.graphs.ingest_state import IngestionState
from app.pipelines.ingestion.page_language_enricher import run_language_detection


def detect_language_node(state: IngestionState) -> dict:
    crawled_path = Path(state["crawled_file"])
    summary = run_language_detection(
        crawled_path,
        save=state.get("save_json", True),
    )

    steps = list(state.get("steps_completed", []))
    steps.append("detect_language")

    return {
        "language_total": summary.total,
        "language_irish": summary.irish,
        "language_english": summary.english,
        "language_unknown": summary.unknown,
        "language_updated": summary.updated,
        "steps_completed": steps,
    }
