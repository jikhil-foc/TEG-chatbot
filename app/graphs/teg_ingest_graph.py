"""LangGraph workflow builder and entry point for full ingestion."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.config.app_settings import settings
from app.graphs.ingest_state import IngestionState
from app.models.embedding import IndexSummary
from app.models.ingest_request import (
    ChunkStepSummary,
    ContentChangeStepSummary,
    CrawlStepSummary,
    IngestionConfig,
    IngestionResult,
    LanguageStepSummary,
)
from app.nodes import ingestion as ingestion_nodes
from app.graphs.node_completion_log import invoke_graph_with_node_logging
from app.utils.langsmith_tracing import build_run_config, configure_langsmith

_compiled_graph = None


def _use_incremental_pipeline(state: IngestionState) -> bool:
    return bool(state.get("incremental")) and not bool(state.get("baseline"))


def _route_after_language(state: IngestionState) -> str:
    if _use_incremental_pipeline(state):
        return "detect_content_changes"
    return "chunk"


def build_ingestion_graph():
    workflow = StateGraph(IngestionState)
    workflow.add_node("crawl", ingestion_nodes.crawl_node)
    workflow.add_node("detect_language", ingestion_nodes.detect_language_node)
    workflow.add_node("chunk", ingestion_nodes.chunk_node)
    workflow.add_node("embed_to_qdrant", ingestion_nodes.embed_to_qdrant_node)
    workflow.add_node("populate_content_registry", ingestion_nodes.populate_content_registry_node)
    workflow.add_node("detect_content_changes", ingestion_nodes.detect_content_changes_node)
    workflow.add_node(
        "sync_changed_sections_to_qdrant",
        ingestion_nodes.sync_changed_sections_node,
    )

    workflow.add_edge(START, "crawl")
    workflow.add_edge("crawl", "detect_language")
    workflow.add_conditional_edges(
        "detect_language",
        _route_after_language,
        {
            "chunk": "chunk",
            "detect_content_changes": "detect_content_changes",
        },
    )
    workflow.add_edge("chunk", "embed_to_qdrant")
    workflow.add_edge("embed_to_qdrant", "populate_content_registry")
    workflow.add_edge("populate_content_registry", END)
    workflow.add_edge("detect_content_changes", "sync_changed_sections_to_qdrant")
    workflow.add_edge("sync_changed_sections_to_qdrant", END)

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
        incremental=config.incremental,
        baseline=config.baseline,
        steps_completed=[],
    )


def _state_to_result(state: IngestionState) -> IngestionResult:
    content_change = None
    if state.get("change_changed_sections") is not None:
        content_change = ContentChangeStepSummary(
            unchanged_sections=state.get("change_unchanged_sections", 0),
            changed_sections=state.get("change_changed_sections", 0),
            removed_sections=state.get("change_removed_sections", 0),
            removed_chunks=state.get("change_removed_chunks", 0),
            changed_chunks=state.get("change_changed_chunks", 0),
            dense_embeddings_generated=state.get("index_dense_embeddings_generated", 0),
        )

    index_summary = None
    if state.get("index_collection_name"):
        index_summary = IndexSummary(
            collection_name=state.get("index_collection_name", ""),
            total_documents=state.get("index_total_documents", 0),
            uploaded=state.get("index_uploaded", 0),
            batches=state.get("index_batches", 0),
            recreated_collection=state.get("index_recreated_collection", False),
            dense_embeddings_generated=state.get("index_dense_embeddings_generated", 0),
        )

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
        index=index_summary,
        content_change=content_change,
    )


def run_ingestion_pipeline(config: IngestionConfig | None = None) -> IngestionResult:
    configure_langsmith()
    config = config or IngestionConfig()
    graph = _get_graph()
    final_state = invoke_graph_with_node_logging(
        graph,
        _build_initial_state(config),
        config=build_run_config(
            run_name="ingestion_pipeline",
            tags=["ingestion"],
            metadata={
                "url": config.url or settings.website_url,
                "max_depth": config.max_depth,
                "recreate": config.recreate,
                "incremental": config.incremental,
                "baseline": config.baseline,
            },
        ),
        pipeline="ingestion",
    )
    return _state_to_result(final_state)
