"""Clarification request node.

Short-circuits retrieval when intent analysis decides the user query is too
vague; returns a follow-up question as the final answer.
"""

from __future__ import annotations

from app.graphs.qa_state import QAState


def clarify_node(state: QAState) -> dict:
    question = state.get("clarification_question") or (
        "Could you provide a bit more detail so I can find the right information?"
    )
    steps = list(state.get("steps_completed", []))
    steps.append("clarify")
    return {
        "answer": question,
        "sources": [],
        "needs_clarification": True,
        "steps_completed": steps,
    }
