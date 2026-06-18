"""Shared search query helpers for retrieval nodes."""

from __future__ import annotations

from app.graphs.qa_state import QAState


def search_query(state: QAState) -> str:
    return state.get("effective_query") or state["query"]


def rerank_search_query(state: QAState) -> str:
    if state.get("retrieval_pass") == "fallback":
        return state.get("fallback_search_query") or search_query(state)
    return search_query(state)


def rerank_language_boost(state: QAState) -> str | None:
    if state.get("retrieval_pass") == "fallback":
        return None
    return state.get("language")
