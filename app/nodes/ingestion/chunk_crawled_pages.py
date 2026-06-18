"""Chunk crawled pages LangGraph node.

Runs the LangChain chunking pipeline on ``crawled_file`` and records chunk
counts in graph state for the ingestion result summary.
"""

from __future__ import annotations

from pathlib import Path

from app.graphs.ingest_state import IngestionState
from app.pipelines.ingestion.langchain_page_chunker import OUTPUT_PATH, run_pipeline


def chunk_node(state: IngestionState) -> dict:
    """Split crawled pages into parent-child chunks and optionally write JSON."""
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
