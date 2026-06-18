"""Greeting response node.

Returns a canned bilingual greeting when intent analysis classifies the input
as hello/thanks/farewell, bypassing retrieval entirely.
"""

from __future__ import annotations

from app.graphs.qa_state import QAState
from app.nodes.shared.canned_responses import DEFAULT_LANGUAGE, GREETING_MESSAGES


def greeting_node(state: QAState) -> dict:
    language = state.get("language", DEFAULT_LANGUAGE)
    kind = state.get("greeting_kind") or "hello"
    messages = GREETING_MESSAGES.get(kind, GREETING_MESSAGES["hello"])
    message = messages.get(language, messages[DEFAULT_LANGUAGE])
    steps = list(state.get("steps_completed", []))
    steps.append("greeting")
    return {
        "answer": message,
        "sources": [],
        "greeting": True,
        "off_topic": False,
        "needs_clarification": False,
        "steps_completed": steps,
    }
