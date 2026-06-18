"""Grounded answer generation node."""

from __future__ import annotations

from app.graphs.qa_state import QAState
from app.nodes.shared.search_query import search_query
from app.services.grounded_answer import generate_answer


def generate_answer_node(state: QAState) -> dict:
    answer = generate_answer(
        search_query(state),
        state.get("reranked", []),
        settings=state["settings"],
        language=state.get("language"),
        context_language=state.get("retrieval_language"),
    )
    steps = list(state.get("steps_completed", []))
    steps.append("generate_answer")
    return {"answer": answer, "steps_completed": steps}
