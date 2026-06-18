"""Primary hybrid retrieval node."""

from __future__ import annotations

from app.graphs.qa_state import QAState
from app.nodes.shared.search_query import search_query


def retrieve_primary_node(state: QAState) -> dict:
    query = search_query(state)
    target_language = state["language"]
    hits = state["retriever"].search(
        query,
        top_k=state["top_k"],
        language=target_language,
    )
    steps = list(state.get("steps_completed", []))
    steps.append("retrieve_primary")
    return {
        "hits": hits,
        "retrieval_language": target_language,
        "retrieval_pass": "primary",
        "steps_completed": steps,
    }
