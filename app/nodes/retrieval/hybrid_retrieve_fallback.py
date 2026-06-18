"""Fallback-language hybrid retrieval node."""

from __future__ import annotations

from app.graphs.qa_state import QAState
from app.nodes.shared.search_query import search_query


def retrieve_fallback_node(state: QAState) -> dict:
    query = state.get("fallback_search_query") or search_query(state)
    fallback_language = state["fallback_language"]
    hits = state["retriever"].search(
        query,
        top_k=state["top_k"],
        language=fallback_language,
    )
    steps = list(state.get("steps_completed", []))
    steps.append("retrieve_fallback")
    return {
        "hits": hits,
        "retrieval_language": fallback_language,
        "retrieval_pass": "fallback",
        "steps_completed": steps,
    }
