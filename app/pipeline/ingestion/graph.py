"""LangGraph workflow builder and entry point for full ingestion."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.core.config import settings
from app.pipeline.embedding.models import IndexSummary
from app.pipeline.ingestion.models import (
    ChunkStepSummary,
    CrawlStepSummary,
    IngestionConfig,
    IngestionResult,
    LanguageStepSummary,
)
from app.pipeline.ingestion.nodes import (
    chunk_node,
    crawl_node,
    detect_language_node,
    embed_to_qdrant_node,
)
from app.pipeline.ingestion.state import IngestionState

_compiled_graph = None


def build_ingestion_graph():
    """Build and compile the linear crawl-to-Qdrant ingestion graph."""
    workflow = StateGraph(IngestionState)
    workflow.add_node("crawl", crawl_node)
    workflow.add_node("detect_language", detect_language_node)
    workflow.add_node("chunk", chunk_node)
    workflow.add_node("embed_to_qdrant", embed_to_qdrant_node)

    workflow.add_edge(START, "crawl")
    workflow.add_edge("crawl", "detect_language")
    workflow.add_edge("detect_language", "chunk")
    workflow.add_edge("chunk", "embed_to_qdrant")
    workflow.add_edge("embed_to_qdrant", END)

    return workflow.compile()


def _get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_ingestion_graph()
    return _compiled_graph


def _build_initial_state(config: IngestionConfig) -> IngestionState:
    return IngestionState(
        url=config.url or settings.website_url,
        max_depth=config.max_depth,
        max_pages=config.max_pages,
        include_pdf=config.include_pdf,
        include_external=config.include_external,
        recreate=config.recreate,
        save_json=config.save_json,
        steps_completed=[],
    )


def _state_to_result(state: IngestionState) -> IngestionResult:
    return IngestionResult(
        source_url=state.get("source_url", ""),
        steps_completed=state.get("steps_completed", []),
        crawl=CrawlStepSummary(
            total=state.get("crawl_total", 0),
            succeeded=state.get("crawl_succeeded", 0),
            failed=state.get("crawl_failed", 0),
            output_file=state.get("crawled_file"),
        ),
        language=LanguageStepSummary(
            total=state.get("language_total", 0),
            irish=state.get("language_irish", 0),
            english=state.get("language_english", 0),
            unknown=state.get("language_unknown", 0),
            updated=state.get("language_updated", 0),
        ),
        chunk=ChunkStepSummary(
            total_pages_loaded=state.get("chunk_total_pages_loaded", 0),
            html_pages_processed=state.get("chunk_html_pages_processed", 0),
            html_parent_chunks=state.get("chunk_html_parent_chunks", 0),
            html_child_chunks=state.get("chunk_html_child_chunks", 0),
            pdf_pages_processed=state.get("chunk_pdf_pages_processed", 0),
            pdf_child_chunks=state.get("chunk_pdf_child_chunks", 0),
            total_child_chunks=state.get("chunk_total_child_chunks", 0),
            output_file=state.get("chunked_file") or None,
        ),
        index=IndexSummary(
            collection_name=state.get("index_collection_name", ""),
            total_documents=state.get("index_total_documents", 0),
            uploaded=state.get("index_uploaded", 0),
            batches=state.get("index_batches", 0),
            recreated_collection=state.get("index_recreated_collection", False),
        ),
    )


def run_ingestion_pipeline(config: IngestionConfig | None = None) -> IngestionResult:
    """Run the full crawl → language → chunk → embed ingestion graph."""
    config = config or IngestionConfig()
    graph = _get_graph()
    final_state = graph.invoke(_build_initial_state(config))
    return _state_to_result(final_state)
