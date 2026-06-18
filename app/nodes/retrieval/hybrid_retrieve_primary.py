"""Primary hybrid retrieval node.

First retrieval pass: searches Qdrant in the user's detected query language
(``state["language"]``) using the effective query from intent analysis.
"""

from __future__ import annotations

from app.graphs.qa_state import QAState
from app.nodes.shared.search_query import search_query


def retrieve_primary_node(state: QAState) -> dict:
    """Retrieve top-k chunks filtered to the user's query language."""
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
