"""Relevance gate for reranked retrieval hits."""

from __future__ import annotations

from app.graphs.qa_state import QAState


def is_relevant_context(state: QAState) -> bool:
    reranked = state.get("reranked", [])
    if not reranked:
        return False
    threshold = state["settings"].rerank_relevance_threshold
    top_score = max(hit.get("rerank_score", 0.0) for hit in reranked)
    return top_score >= threshold
