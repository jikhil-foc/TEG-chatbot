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
from app.pipeline.qa.nodes import (
    citations_node,
    detect_language_node,
    fallback_node,
    generate_answer_node,
    rerank_node,
    retrieve_node,
    validation_node,
)
from app.pipeline.qa.state import QAState

logger = logging.getLogger(__name__)

_compiled_graph = None


def _relevance_gate(state: QAState) -> str:
    """Route to answer generation when reranked context is relevant enough."""
    reranked = state.get("reranked", [])
    if not reranked:
        return "fallback"

    threshold = state["settings"].rerank_relevance_threshold
    top_score = max(hit.get("rerank_score", 0.0) for hit in reranked)
    return "generate_answer" if top_score >= threshold else "fallback"


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
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("rerank", rerank_node)
    workflow.add_node("fallback", fallback_node)
    workflow.add_node("generate_answer", generate_answer_node)
    workflow.add_node("citations", citations_node)
    workflow.add_node("validation", validation_node)

    workflow.add_edge(START, "detect_language")
    workflow.add_edge("detect_language", "retrieve")
    workflow.add_edge("retrieve", "rerank")
    workflow.add_conditional_edges(
        "rerank",
        _relevance_gate,
        {"generate_answer": "generate_answer", "fallback": "fallback"},
    )
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


def run_qa_pipeline(
    query: str,
    top_k: int = 10,
    rerank_top_n: int = 5,
    retriever: HybridRetriever | None = None,
    settings: EmbeddingSettings | None = None,
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

    initial_state: QAState = {
        "query": query,
        "top_k": top_k,
        "rerank_top_n": rerank_top_n,
        "retriever": retriever,
        "settings": settings,
        "max_retries": settings.qa_max_validation_retries,
        "retry_count": 0,
        "steps_completed": [],
    }

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
