"""LangGraph workflow builder and entry point for question answering.

Wires the QA steps -- detect language, hybrid retrieval, Cohere rerank, relevance
gate, answer generation, citation extraction, and an LLM validation retry loop
-- into a compiled graph, mirroring the ingestion graph in
:mod:`app.pipeline.ingestion.graph`.
"""

from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

from app.core.langsmith import build_run_config, configure_langsmith
from app.pipeline.embedding.config import EmbeddingSettings, get_embedding_settings
from app.pipeline.embedding.retriever import HybridRetriever
from app.pipeline.llm.models import AnswerResult
from app.pipeline.qa.conversation import ConversationMessage
from app.pipeline.qa.nodes import (
    analyze_query_node,
    citations_node,
    clarify_node,
    detect_language_node,
    fallback_node,
    generate_answer_node,
    greeting_node,
    is_relevant_context,
    rerank_node,
    retrieve_fallback_node,
    retrieve_primary_node,
    translate_fallback_query_node,
    validation_node,
)
from app.pipeline.qa.state import QAState

logger = logging.getLogger(__name__)

_compiled_graph = None


def _route_after_analyze(state: QAState) -> str:
    """Handle greetings, reject off-topic queries, clarify, or continue."""
    if state.get("greeting"):
        return "greeting"
    if state.get("off_topic"):
        return "fallback"
    if state.get("needs_clarification"):
        return "clarify"
    return "retrieve_primary"


def _route_after_primary_rerank(state: QAState) -> str:
    """Continue to answer generation or try fallback-language retrieval."""
    if is_relevant_context(state):
        return "generate_answer"
    return "translate_fallback_query"


def _route_after_fallback_rerank(state: QAState) -> str:
    """Answer from fallback context or return a canned no-answer message."""
    if is_relevant_context(state):
        return "generate_answer"
    return "fallback"


def _route_after_rerank(state: QAState) -> str:
    """Route after rerank based on which retrieval pass just completed."""
    if state.get("retrieval_pass") == "fallback":
        return _route_after_fallback_rerank(state)
    return _route_after_primary_rerank(state)


def _route_validation(state: QAState) -> str:
    """Loop back to regenerate the answer when validation fails with retries left."""
    if state.get("validation_passed"):
        return END
    if state.get("retry_count", 0) < state.get("max_retries", 0):
        return "generate_answer"
    return END


def build_qa_graph():
    """Build and compile the QA workflow graph."""
    workflow = StateGraph(QAState)
    workflow.add_node("detect_language", detect_language_node)
    workflow.add_node("analyze_query", analyze_query_node)
    workflow.add_node("clarify", clarify_node)
    workflow.add_node("greeting", greeting_node)
    workflow.add_node("retrieve_primary", retrieve_primary_node)
    workflow.add_node("translate_fallback_query", translate_fallback_query_node)
    workflow.add_node("retrieve_fallback", retrieve_fallback_node)
    workflow.add_node("rerank", rerank_node)
    workflow.add_node("fallback", fallback_node)
    workflow.add_node("generate_answer", generate_answer_node)
    workflow.add_node("citations", citations_node)
    workflow.add_node("validation", validation_node)

    workflow.add_edge(START, "detect_language")
    workflow.add_edge("detect_language", "analyze_query")
    workflow.add_conditional_edges(
        "analyze_query",
        _route_after_analyze,
        {
            "greeting": "greeting",
            "fallback": "fallback",
            "clarify": "clarify",
            "retrieve_primary": "retrieve_primary",
        },
    )
    workflow.add_edge("greeting", END)
    workflow.add_edge("clarify", END)
    workflow.add_edge("retrieve_primary", "rerank")
    workflow.add_conditional_edges(
        "rerank",
        _route_after_rerank,
        {
            "generate_answer": "generate_answer",
            "translate_fallback_query": "translate_fallback_query",
            "fallback": "fallback",
        },
    )
    workflow.add_edge("translate_fallback_query", "retrieve_fallback")
    workflow.add_edge("retrieve_fallback", "rerank")
    workflow.add_edge("fallback", END)
    workflow.add_edge("generate_answer", "citations")
    workflow.add_edge("citations", "validation")
    workflow.add_conditional_edges(
        "validation",
        _route_validation,
        {"generate_answer": "generate_answer", END: END},
    )

    return workflow.compile()


def _get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_qa_graph()
    return _compiled_graph


def reset_qa_graph() -> None:
    """Clear the cached compiled graph (used in tests)."""
    global _compiled_graph
    _compiled_graph = None


def get_qa_graph():
    """Return the compiled QA LangGraph workflow."""
    return _get_graph()


def build_qa_initial_state(
    query: str,
    *,
    top_k: int,
    rerank_top_n: int,
    retriever: HybridRetriever,
    settings: EmbeddingSettings,
    messages: list[ConversationMessage] | None = None,
    session_id: str | None = None,
) -> QAState:
    """Build the initial state dict for QA graph invoke/stream."""
    return {
        "query": query,
        "messages": messages or [],
        "session_id": session_id,
        "top_k": top_k,
        "rerank_top_n": rerank_top_n,
        "retriever": retriever,
        "settings": settings,
        "max_retries": settings.qa_max_validation_retries,
        "retry_count": 0,
        "steps_completed": [],
    }


def run_qa_pipeline(
    query: str,
    top_k: int = 10,
    rerank_top_n: int = 5,
    retriever: HybridRetriever | None = None,
    settings: EmbeddingSettings | None = None,
    messages: list[ConversationMessage] | None = None,
    session_id: str | None = None,
) -> AnswerResult:
    """Answer ``query`` end-to-end through the QA LangGraph workflow."""
    settings = settings or get_embedding_settings()
    retriever = retriever or HybridRetriever.from_settings(settings)

    logger.info(
        "Running QA graph (top_k=%d, rerank_top_n=%d): %r",
        top_k,
        rerank_top_n,
        query,
    )

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

    final_state = _get_graph().invoke(
        initial_state,
        config=build_run_config(
            run_name="qa_pipeline",
            tags=["qa", "ask"],
            metadata={"query": query[:500]},
        ),
    )

    return AnswerResult(
        answer=final_state.get("answer", ""),
        language=final_state.get("language"),
        sources=final_state.get("sources", []),
    )
