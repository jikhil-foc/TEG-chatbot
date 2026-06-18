"""Crawl TEG website ingestion node."""

from __future__ import annotations

from app.graphs.ingest_state import IngestionState
from app.pipelines.ingestion.langchain_page_chunker import INPUT_PATH
from app.pipelines.ingestion.teg_site_crawler import run_crawl, save_pages_json


def crawl_node(state: IngestionState) -> dict:
    start_url = state["url"]
    pages = run_crawl(
        url=start_url,
        max_depth=state["max_depth"],
        max_pages=state["max_pages"],
        include_pdf=state["include_pdf"],
        include_external=state["include_external"],
        save_json=False,
    )

    crawled_file: str | None = None
    if state.get("save_json", True):
        crawled_file = str(save_pages_json(pages, source_url=start_url))

    succeeded = sum(1 for page in pages if page.success)
    steps = list(state.get("steps_completed", []))
    steps.append("crawl")

    return {
        "source_url": start_url,
        "crawled_file": crawled_file or str(INPUT_PATH),
        "crawl_total": len(pages),
        "crawl_succeeded": succeeded,
        "crawl_failed": len(pages) - succeeded,
        "steps_completed": steps,
    }
