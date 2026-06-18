"""Translate query for fallback retrieval node.

When primary-language retrieval scores poorly, this node LLM-translates the
query into ``fallback_language`` before the second hybrid search pass.
"""

from __future__ import annotations

from app.graphs.qa_state import QAState
from app.nodes.shared.search_query import search_query
from app.qa.en_ga_query_translator import translate_query


def translate_fallback_query_node(state: QAState) -> dict:
    query = search_query(state)
    fallback_language = state["fallback_language"]
    translated = translate_query(
        query,
        fallback_language,
        settings=state["settings"],
    )
    steps = list(state.get("steps_completed", []))
    steps.append("translate_fallback_query")
    return {
        "fallback_search_query": translated,
        "steps_completed": steps,
    }
