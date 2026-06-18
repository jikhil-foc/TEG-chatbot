"""Weak context fallback node."""

from __future__ import annotations

from app.graphs.qa_state import QAState
from app.nodes.shared.canned_responses import DEFAULT_LANGUAGE, FALLBACK_MESSAGES


def fallback_node(state: QAState) -> dict:
    language = state.get("language", DEFAULT_LANGUAGE)
    message = FALLBACK_MESSAGES.get(language, FALLBACK_MESSAGES[DEFAULT_LANGUAGE])
    steps = list(state.get("steps_completed", []))
    steps.append("fallback")
    return {
        "answer": message,
        "sources": [],
        "fallback": True,
        "steps_completed": steps,
    }
