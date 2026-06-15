"""LangGraph node functions for the question-answering pipeline."""

from __future__ import annotations

import re

from app.pipeline.llm.answerer import generate_answer
from app.pipeline.llm.models import Source
from app.pipeline.llm.reranker import rerank
from app.pipeline.qa.state import QAState
from app.pipeline.qa.validator import validate_answer
from app.utils.crawler.text import detect_language_from_text

_DEFAULT_LANGUAGE = "English"

# Canned fallback answers keyed by detected language, used when the relevance
# gate decides the retrieved context is too weak to answer from.
_FALLBACK_MESSAGES = {
    "English": "I don't have enough information based on the available content.",
    "Irish": "Níl go leor eolais agam bunaithe ar an ábhar atá ar fáil.",
}

# Matches inline citation markers such as ``[1]`` or ``[12]`` in an answer.
_CITATION_RE = re.compile(r"\[(\d+)\]")


def _to_source(hit: dict) -> Source:
    """Map a reranked retriever hit to a :class:`Source`."""
    metadata = hit.get("metadata") or {}
    return Source(
        chunk_id=hit.get("chunk_id", ""),
        url=metadata.get("url", ""),
        title=metadata.get("title", ""),
        score=float(hit.get("score", 0.0)),
        rerank_score=float(hit.get("rerank_score", 0.0)),
    )


def detect_language_node(state: QAState) -> dict:
    """Detect the query language so the answer can reply in kind."""
    language = detect_language_from_text(state["query"]) or _DEFAULT_LANGUAGE
    steps = list(state.get("steps_completed", []))
    steps.append("detect_language")
    return {"language": language, "steps_completed": steps}


def retrieve_node(state: QAState) -> dict:
    """Run hybrid dense + BM25 retrieval for the query."""
    hits = state["retriever"].search(state["query"], top_k=state["top_k"])
    steps = list(state.get("steps_completed", []))
    steps.append("retrieve")
    return {"hits": hits, "steps_completed": steps}


def rerank_node(state: QAState) -> dict:
    """Rescore retrieved hits with the BGE cross-encoder reranker."""
    reranked = rerank(state["query"], state.get("hits", []), top_n=state["rerank_top_n"])
    steps = list(state.get("steps_completed", []))
    steps.append("rerank")
    return {"reranked": reranked, "steps_completed": steps}


def fallback_node(state: QAState) -> dict:
    """Return a canned no-answer response in the detected language."""
    language = state.get("language", _DEFAULT_LANGUAGE)
    message = _FALLBACK_MESSAGES.get(language, _FALLBACK_MESSAGES[_DEFAULT_LANGUAGE])
    steps = list(state.get("steps_completed", []))
    steps.append("fallback")
    return {
        "answer": message,
        "sources": [],
        "fallback": True,
        "steps_completed": steps,
    }


def generate_answer_node(state: QAState) -> dict:
    """Generate a grounded, cited answer from the reranked context."""
    answer = generate_answer(
        state["query"],
        state.get("reranked", []),
        settings=state["settings"],
        language=state.get("language"),
    )
    steps = list(state.get("steps_completed", []))
    steps.append("generate_answer")
    return {"answer": answer, "steps_completed": steps}


def citations_node(state: QAState) -> dict:
    """Keep only the reranked sources actually cited by the answer."""
    reranked = state.get("reranked", [])
    answer = state.get("answer", "")

    cited_indices: list[int] = []
    for match in _CITATION_RE.findall(answer):
        index = int(match)
        if 1 <= index <= len(reranked) and index not in cited_indices:
            cited_indices.append(index)

    if cited_indices:
        sources = [_to_source(reranked[index - 1]) for index in cited_indices]
    else:
        sources = [_to_source(hit) for hit in reranked]

    steps = list(state.get("steps_completed", []))
    steps.append("citations")
    return {"sources": sources, "steps_completed": steps}


def validation_node(state: QAState) -> dict:
    """Validate answer groundedness/citations and track retry attempts."""
    passed = validate_answer(
        state["query"],
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
