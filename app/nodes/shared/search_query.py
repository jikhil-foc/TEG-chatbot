"""Shared search query helpers for retrieval nodes."""

from __future__ import annotations

from app.graphs.qa_state import QAState


def search_query(state: QAState) -> str:
    """Return the query used for retrieval after intent analysis rewrites."""
    return state.get("effective_query") or state["query"]


def rerank_search_query(state: QAState) -> str:
    """Pick the query string passed to Cohere rerank for the current pass."""
    if state.get("retrieval_pass") == "fallback":
        return state.get("fallback_search_query") or search_query(state)
    return search_query(state)


def rerank_language_boost(state: QAState) -> str | None:
    """Return the language boost target, disabled on the fallback pass.

    Fallback retrieval already filters by ``fallback_language``; applying the
    boost again would double-favour that language in reranking.
    """
