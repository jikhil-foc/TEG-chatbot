"""Log concise summaries when LangGraph nodes complete."""

from __future__ import annotations

import logging
from collections.abc import Iterator, Mapping
from typing import Any

logger = logging.getLogger(__name__)

_PIPELINE_QA = "qa"
_PIPELINE_INGESTION = "ingestion"


def _truncate(text: str, limit: int = 80) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3]}..."


def _top_rerank_score(reranked: list[dict[str, Any]]) -> float:
    if not reranked:
        return 0.0
    return max(hit.get("rerank_score", 0.0) for hit in reranked)


def _summarize_qa_node(node_name: str, update: Mapping[str, Any]) -> str:
    if node_name == "detect_language":
        return (
            f"language={update.get('language')} "
            f"fallback={update.get('fallback_language')}"
        )

    if node_name == "analyze_query":
        if update.get("greeting"):
            return f"greeting route (kind={update.get('greeting_kind', 'hello')})"
        if update.get("off_topic"):
            return "off-topic route"
        if update.get("needs_clarification"):
            return "clarification route"
        effective_query = update.get("effective_query", "")
        return f"on-topic query={_truncate(str(effective_query))!r}"

    if node_name == "clarify":
        return "clarification answer returned"

    if node_name == "greeting":
        return f"greeting answer (kind={update.get('greeting_kind', 'hello')})"

    if node_name in {"retrieve_primary", "retrieve_fallback"}:
        return (
            f"hits={len(update.get('hits', []))} "
            f"language={update.get('retrieval_language')} "
            f"pass={update.get('retrieval_pass')}"
        )

    if node_name == "translate_fallback_query":
        translated = str(update.get("fallback_search_query", ""))
        return f"translated_query={_truncate(translated)!r}"

    if node_name == "rerank":
        reranked = list(update.get("reranked", []))
        return (
            f"reranked={len(reranked)} "
            f"top_score={_top_rerank_score(reranked):.3f}"
        )

    if node_name == "fallback":
        return "weak-context fallback answer"

    if node_name == "generate_answer":
        answer = str(update.get("answer", ""))
        return f"answer_chars={len(answer)}"

    if node_name == "citations":
        return f"sources={len(update.get('sources', []))}"

    if node_name == "validation":
        return (
            f"passed={bool(update.get('validation_passed'))} "
            f"retry_count={update.get('retry_count', 0)}"
        )

    return "completed"


def _summarize_ingestion_node(node_name: str, update: Mapping[str, Any]) -> str:
    if node_name == "crawl":
        return (
            f"total={update.get('crawl_total', 0)} "
            f"succeeded={update.get('crawl_succeeded', 0)} "
            f"failed={update.get('crawl_failed', 0)}"
        )

    if node_name == "detect_language":
        return (
            f"total={update.get('language_total', 0)} "
            f"irish={update.get('language_irish', 0)} "
            f"english={update.get('language_english', 0)} "
            f"unknown={update.get('language_unknown', 0)} "
            f"updated={update.get('language_updated', 0)}"
        )

    if node_name == "chunk":
        return (
            f"pages_loaded={update.get('chunk_total_pages_loaded', 0)} "
            f"child_chunks={update.get('chunk_total_child_chunks', 0)}"
        )

    if node_name == "embed_to_qdrant":
        return (
            f"uploaded={update.get('index_uploaded', 0)}/"
            f"{update.get('index_total_documents', 0)} "
            f"batches={update.get('index_batches', 0)} "
            f"collection={update.get('index_collection_name', '')}"
        )

    if node_name == "populate_content_registry":
        return (
            f"pages={update.get('registry_pages', 0)} "
            f"sections={update.get('registry_sections', 0)} "
            f"chunks={update.get('registry_chunks', 0)}"
        )

    if node_name == "detect_content_changes":
        return (
            f"unchanged={update.get('change_unchanged_sections', 0)} "
            f"changed={update.get('change_changed_sections', 0)} "
            f"removed_sections={update.get('change_removed_sections', 0)} "
            f"removed_chunks={update.get('change_removed_chunks', 0)}"
        )

    if node_name == "sync_changed_sections_to_qdrant":
        return (
            f"uploaded={update.get('index_uploaded', 0)} "
            f"changed_chunks={update.get('change_changed_chunks', 0)} "
            f"removed_chunks={update.get('change_removed_chunks', 0)} "
            f"embeddings={update.get('index_dense_embeddings_generated', 0)}"
        )

    return "completed"


def build_node_summary(
    pipeline: str,
    node_name: str,
    update: Mapping[str, Any],
) -> str:
    """Return a short human-readable summary for a completed graph node."""
    if pipeline == _PIPELINE_QA:
        return _summarize_qa_node(node_name, update)
    if pipeline == _PIPELINE_INGESTION:
        return _summarize_ingestion_node(node_name, update)
    return "completed"


def log_node_completed(
    pipeline: str,
    node_name: str,
    update: Mapping[str, Any],
) -> None:
    """Emit an INFO log line summarizing a completed graph node."""
    summary = build_node_summary(pipeline, node_name, update)
    logger.info("[%s] node %s completed: %s", pipeline, node_name, summary)


def stream_graph_with_node_logging(
    graph: Any,
    initial_state: Mapping[str, Any],
    config: Mapping[str, Any] | None,
    *,
    pipeline: str,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Stream graph updates and log a summary after each node completes."""
    for chunk in graph.stream(initial_state, config=config, stream_mode="updates"):
        for node_name, update in chunk.items():
            log_node_completed(pipeline, node_name, update)
            yield node_name, update


def invoke_graph_with_node_logging(
    graph: Any,
    initial_state: Mapping[str, Any],
    config: Mapping[str, Any] | None,
    *,
    pipeline: str,
) -> dict[str, Any]:
    """Run a graph to completion, logging a summary after each node."""
    accumulated = dict(initial_state)
    for node_name, update in stream_graph_with_node_logging(
        graph,
        initial_state,
        config,
        pipeline=pipeline,
    ):
        accumulated.update(update)
        _ = node_name
    return accumulated
