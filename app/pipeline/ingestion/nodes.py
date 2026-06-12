"""LangGraph node functions for the ingestion pipeline."""

from __future__ import annotations

from pathlib import Path

from app.pipeline.chunk_pipeline import INPUT_PATH, OUTPUT_PATH, run_pipeline
from app.pipeline.crawl_website import run_crawl, save_pages_json
from app.pipeline.embedding.config import get_embedding_settings
from app.pipeline.embedding_pipeline import run_indexing
from app.pipeline.ingestion.state import IngestionState
from app.pipeline.language_pipeline import run_language_detection


def crawl_node(state: IngestionState) -> dict:
    """Crawl the website and persist results to JSON."""
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


def detect_language_node(state: IngestionState) -> dict:
    """Enrich crawled pages with language tags."""
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


def chunk_node(state: IngestionState) -> dict:
    """Chunk crawled data into child-level chunks."""
    input_path = Path(state["crawled_file"])
    output_path = OUTPUT_PATH if state.get("save_json", True) else None
    result = run_pipeline(input_path, output_path)

    steps = list(state.get("steps_completed", []))
    steps.append("chunk")

    summary = result.summary
    return {
        "chunked_file": str(OUTPUT_PATH) if state.get("save_json", True) else "",
        "chunk_total_pages_loaded": summary.total_pages_loaded,
        "chunk_html_pages_processed": summary.html_pages_processed,
        "chunk_html_parent_chunks": summary.html_parent_chunks,
        "chunk_html_child_chunks": summary.html_child_chunks,
        "chunk_pdf_pages_processed": summary.pdf_pages_processed,
        "chunk_pdf_child_chunks": summary.pdf_child_chunks,
        "chunk_total_child_chunks": summary.total_child_chunks,
        "steps_completed": steps,
    }


def embed_to_qdrant_node(state: IngestionState) -> dict:
    """Embed chunks and upload to Qdrant."""
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
