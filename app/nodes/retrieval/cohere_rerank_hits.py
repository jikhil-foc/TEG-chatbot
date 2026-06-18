"""Cohere rerank node."""

from __future__ import annotations

from app.graphs.qa_state import QAState
from app.nodes.shared.search_query import rerank_language_boost, rerank_search_query
from app.services.cohere_reranker import rerank


def rerank_node(state: QAState) -> dict:
    search_query = rerank_search_query(state)
    reranked = rerank(
        search_query,
        state.get("hits", []),
        top_n=state["rerank_top_n"],
        settings=state["settings"],
        language=rerank_language_boost(state),
    )
    steps = list(state.get("steps_completed", []))
    steps.append("rerank")
    return {"reranked": reranked, "steps_completed": steps}
