"""Streaming QA orchestration for Server-Sent Events responses."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from app.utils.langsmith_tracing import build_run_config, configure_langsmith
from app.config.embedding_settings import EmbeddingSettings, get_embedding_settings
from app.pipelines.retrieval.hybrid_retriever import HybridRetriever
from app.qa.conversation_history import ConversationMessage
from app.graphs.qa_rag_graph import build_qa_initial_state, get_qa_graph
from app.graphs.qa_state import QAState
from app.qa.related_question_generator import generate_related_questions

logger = logging.getLogger(__name__)

_TERMINAL_NODES = frozenset({"clarify", "fallback", "greeting"})
_STATUS_STEP_ALIASES = {
    "generate_answer": "generate",
    "retrieve_primary": "retrieve",
}


def _status_step(node_name: str) -> str:
    return _STATUS_STEP_ALIASES.get(node_name, node_name)


def _serialize_sources(sources: list[Any]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for source in sources:
        if hasattr(source, "model_dump"):
            serialized.append(source.model_dump())
        elif isinstance(source, dict):
            serialized.append(source)
    return serialized


def _should_generate_related_questions(state: QAState) -> bool:
    if state.get("needs_clarification"):
        return False
    if state.get("off_topic") or state.get("fallback"):
        return False
    return bool(state.get("answer", "").strip())


def _maybe_related_questions(state: QAState) -> list[str]:
    if not _should_generate_related_questions(state):
        return []

    search_query = state.get("effective_query") or state.get("query", "")
    return generate_related_questions(
        search_query,
        state.get("answer", ""),
        language=state.get("language"),
        settings=state.get("settings"),
    )


def _done_event(query: str, state: QAState) -> dict[str, Any]:
    return {
        "type": "done",
        "query": query,
        "answer": state.get("answer", ""),
        "language": state.get("language"),
        "sources": _serialize_sources(state.get("sources", [])),
        "clarification": bool(state.get("needs_clarification")),
        "off_topic": bool(state.get("off_topic")),
        "related_questions": _maybe_related_questions(state),
    }


def _yield_answer_tokens(answer: str) -> Iterator[dict[str, Any]]:
    """Emit the final answer as SSE token events."""
    if not answer:
        return
    yield {"type": "token", "content": answer}


def stream_qa_pipeline(
    query: str,
    top_k: int,
    rerank_top_n: int,
    retriever: HybridRetriever,
    settings: EmbeddingSettings | None = None,
    messages: list[ConversationMessage] | None = None,
    session_id: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield SSE-friendly events by streaming the LangGraph QA workflow."""
    settings = settings or get_embedding_settings()
    configure_langsmith()

    initial_state = build_qa_initial_state(
        query,
        top_k=top_k,
        rerank_top_n=rerank_top_n,
        retriever=retriever,
        settings=settings,
        messages=messages,
        session_id=session_id,
    )
    config = build_run_config(
        run_name="qa_pipeline_stream",
        tags=["qa", "ask", "stream"],
        metadata={"query": query[:500]},
    )

    graph = get_qa_graph()
    accumulated: QAState = dict(initial_state)

    logger.info("Streaming QA graph (top_k=%d, rerank_top_n=%d): %r", top_k, rerank_top_n, query)

    for chunk in graph.stream(initial_state, config=config, stream_mode="updates"):
        for node_name, update in chunk.items():
            accumulated.update(update)
            yield {"type": "status", "step": _status_step(node_name)}

            if node_name in _TERMINAL_NODES:
                answer = accumulated.get("answer", "")
                yield from _yield_answer_tokens(answer)
                yield _done_event(query, accumulated)
                return

    answer = accumulated.get("answer", "")
    yield from _yield_answer_tokens(answer)
    yield _done_event(query, accumulated)
