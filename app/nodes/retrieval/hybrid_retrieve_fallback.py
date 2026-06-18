"""Fallback-language hybrid retrieval node.

Second retrieval pass after primary rerank scores fall below threshold: searches
in ``fallback_language`` using the LLM-translated ``fallback_search_query``.
"""

from __future__ import annotations

from app.graphs.qa_state import QAState
from app.nodes.shared.search_query import search_query


def retrieve_fallback_node(state: QAState) -> dict:
    """Retrieve top-k chunks in the opposite language from the user's query."""
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
