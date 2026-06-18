"""Detect query language node.

Sets ``language`` and ``fallback_language`` (Irish ↔ English) used by the
bilingual retrieval and reranking strategy in the QA graph.
"""

from __future__ import annotations

from app.graphs.qa_state import QAState
from app.nodes.shared.canned_responses import DEFAULT_LANGUAGE
from app.services.language_detector import detect_query_language
from app.utils.language import opposite_language


def detect_language_node(state: QAState) -> dict:
    language = detect_query_language(state["query"]) or DEFAULT_LANGUAGE
    steps = list(state.get("steps_completed", []))
    steps.append("detect_language")
    return {
        "language": language,
        "fallback_language": opposite_language(language),
        "retrieval_language": None,
        "steps_completed": steps,
    }
