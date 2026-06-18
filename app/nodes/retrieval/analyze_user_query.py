"""Analyze user query node."""

from __future__ import annotations

from app.graphs.qa_state import QAState
from app.qa.query_intent_analyzer import analyze_conversation


def analyze_query_node(state: QAState) -> dict:
    analysis = analyze_conversation(
        state["query"],
        messages=state.get("messages") or [],
        session_id=state.get("session_id"),
        settings=state["settings"],
    )
    steps = list(state.get("steps_completed", []))
    steps.append("analyze_query")

    if analysis.status == "greeting":
        return {
            "greeting": True,
            "greeting_kind": analysis.greeting_kind or "hello",
            "off_topic": False,
            "needs_clarification": False,
            "clarification_question": None,
            "steps_completed": steps,
        }

    if analysis.status == "off_topic":
        return {
            "off_topic": True,
            "needs_clarification": False,
            "clarification_question": None,
            "steps_completed": steps,
        }

    if analysis.status == "needs_clarification":
        return {
            "off_topic": False,
            "needs_clarification": True,
            "clarification_question": analysis.clarification_question,
            "steps_completed": steps,
        }

    return {
        "off_topic": False,
        "greeting": False,
        "needs_clarification": False,
        "effective_query": analysis.effective_query,
        "clarification_question": None,
        "steps_completed": steps,
    }
