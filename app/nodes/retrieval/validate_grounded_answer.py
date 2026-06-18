"""Answer validation node.

Checks whether the generated answer is grounded in the reranked context. The
graph may loop back to ``generate_answer`` when validation fails and retries
remain (see ``_route_validation`` in :mod:`app.graphs.qa_rag_graph`).
"""

from __future__ import annotations

from app.graphs.qa_state import QAState
from app.nodes.shared.search_query import search_query
from app.qa.answer_topic_validator import validate_answer


def validation_node(state: QAState) -> dict:
    """Validate the answer against retrieved context and increment retry count."""
    passed = validate_answer(
        search_query(state),
        state.get("answer", ""),
        state.get("reranked", []),
        settings=state["settings"],
    )
    steps = list(state.get("steps_completed", []))
    steps.append("validation")
    return {
        "validation_passed": passed,
        "retry_count": state.get("retry_count", 0) + 1,
        "steps_completed": steps,
    }
