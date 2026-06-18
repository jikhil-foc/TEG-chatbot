"""Answer validation node."""

from __future__ import annotations

from app.graphs.qa_state import QAState
from app.nodes.shared.search_query import search_query
from app.qa.answer_topic_validator import validate_answer


def validation_node(state: QAState) -> dict:
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
