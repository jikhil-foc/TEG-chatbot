"""LangGraph workflow builder and entry point for question answering."""

from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

from app.config.embedding_settings import EmbeddingSettings, get_embedding_settings
from app.graphs.qa_state import QAState
from app.models.answer_types import AnswerResult
from app.nodes import retrieval as retrieval_nodes
from app.pipelines.retrieval.hybrid_retriever import HybridRetriever
from app.qa.conversation_history import ConversationMessage
from app.utils.langsmith_tracing import build_run_config, configure_langsmith

logger = logging.getLogger(__name__)

_compiled_graph = None


def _route_after_analyze(state: QAState) -> str:
    if state.get("greeting"):
        return "greeting"
    if state.get("off_topic"):
        return "fallback"
    if state.get("needs_clarification"):
        return "clarify"
    return "retrieve_primary"


def _route_after_primary_rerank(state: QAState) -> str:
    if retrieval_nodes.is_relevant_context(state):
        return "generate_answer"
    return "translate_fallback_query"


def _route_after_fallback_rerank(state: QAState) -> str:
    if retrieval_nodes.is_relevant_context(state):
        return "generate_answer"
    return "fallback"


def _route_after_rerank(state: QAState) -> str:
    if state.get("retrieval_pass") == "fallback":
        return _route_after_fallback_rerank(state)
    return _route_after_primary_rerank(state)


def _route_validation(state: QAState) -> str:
    if state.get("validation_passed"):
        return END
    if state.get("retry_count", 0) < state.get("max_retries", 0):
        return "generate_answer"
    return END


def build_qa_graph():
    workflow = StateGraph(QAState)
    workflow.add_node("detect_language", retrieval_nodes.detect_language_node)
    workflow.add_node("analyze_query", retrieval_nodes.analyze_query_node)
    workflow.add_node("clarify", retrieval_nodes.clarify_node)
    workflow.add_node("greeting", retrieval_nodes.greeting_node)
    workflow.add_node("retrieve_primary", retrieval_nodes.retrieve_primary_node)
    workflow.add_node(
        "translate_fallback_query", retrieval_nodes.translate_fallback_query_node
    )
    workflow.add_node("retrieve_fallback", retrieval_nodes.retrieve_fallback_node)
    workflow.add_node("rerank", retrieval_nodes.rerank_node)
    workflow.add_node("fallback", retrieval_nodes.fallback_node)
    workflow.add_node("generate_answer", retrieval_nodes.generate_answer_node)
    workflow.add_node("citations", retrieval_nodes.citations_node)
    workflow.add_node("validation", retrieval_nodes.validation_node)

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
    global _compiled_graph
    _compiled_graph = None


def get_qa_graph():
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
