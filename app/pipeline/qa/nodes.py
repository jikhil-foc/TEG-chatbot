"""LangGraph node functions for the question-answering pipeline."""

from __future__ import annotations

import re

from app.pipeline.llm.answerer import generate_answer
from app.pipeline.llm.models import Source
from app.pipeline.llm.reranker import rerank
from app.pipeline.qa.query_analyzer import analyze_conversation
from app.pipeline.qa.state import QAState
from app.pipeline.qa.translator import translate_query
from app.pipeline.qa.validator import validate_answer
from app.pipeline.crawl.text import detect_query_language
from app.pipeline.language.utils import opposite_language

_DEFAULT_LANGUAGE = "English"

# Canned fallback answers keyed by detected language, used when the relevance
# gate decides the retrieved context is too weak to answer from.
_FALLBACK_MESSAGES = {
    "English": "Please ask questions related to TEG. I'm here to help with TEG website content.",
    "Irish": "Cuir ceist a bhaineann le TEG, le do thoil. Tá mé anseo chun cabhrú le hábhar láithreán TEG.",
}

_GREETING_MESSAGES = {
    "hello": {
        "English": (
            "Hello! I can help answer questions about TEG based on our published "
            "content. What would you like to know?"
        ),
        "Irish": (
            "Dia dhuit! Is féidir liom cabhrú le ceisteanna faoi TEG bunaithe ar "
            "ár n-ábhar foilsithe. Cad ba mhaith leat a fháil amach?"
        ),
    },
    "thanks": {
        "English": "You're welcome! Let me know if you have any other TEG questions.",
        "Irish": "Tá fáilte romhat! Cuir ceist eile faoi TEG orm más gá.",
    },
    "farewell": {
        "English": (
            "Goodbye! Feel free to come back if you have more questions about TEG."
        ),
        "Irish": (
            "Slán! Tar ar ais má bhíonn tuilleadh ceisteanna agat faoi TEG."
        ),
    },
}

# Matches inline citation markers such as ``[1]`` or ``[12]`` in an answer.
_CITATION_RE = re.compile(r"\[(\d+)\]")

_OFF_TOPIC_MARKERS = tuple(
    phrase.lower()
    for phrase in (
        *_FALLBACK_MESSAGES.values(),
        "Please ask questions related to TEG.",
        "I'm here to help with TEG website content.",
    )
)


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


def _search_query(state: QAState) -> str:
    return state.get("effective_query") or state["query"]


def _rerank_search_query(state: QAState) -> str:
    if state.get("retrieval_pass") == "fallback":
        return state.get("fallback_search_query") or _search_query(state)
    return _search_query(state)


def _rerank_language_boost(state: QAState) -> str | None:
    if state.get("retrieval_pass") == "fallback":
        return None
    return state.get("language")


def detect_language_node(state: QAState) -> dict:
    """Detect the query language so the answer can reply in kind."""
    language = detect_query_language(state["query"]) or _DEFAULT_LANGUAGE
    steps = list(state.get("steps_completed", []))
    steps.append("detect_language")
    return {
        "language": language,
        "fallback_language": opposite_language(language),
        "retrieval_language": None,
        "steps_completed": steps,
    }


def analyze_query_node(state: QAState) -> dict:
    """Decide whether to clarify or rewrite the query for retrieval."""
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


def greeting_node(state: QAState) -> dict:
    """Return a warm canned reply for greetings, thanks, and goodbyes."""
    language = state.get("language", _DEFAULT_LANGUAGE)
    kind = state.get("greeting_kind") or "hello"
    messages = _GREETING_MESSAGES.get(kind, _GREETING_MESSAGES["hello"])
    message = messages.get(language, messages[_DEFAULT_LANGUAGE])
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


def clarify_node(state: QAState) -> dict:
    """Ask the user for missing details before retrieval."""
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


def retrieve_primary_node(state: QAState) -> dict:
    """Run hybrid retrieval scoped to the detected query language."""
    search_query = _search_query(state)
    target_language = state["language"]
    hits = state["retriever"].search(
        search_query,
        top_k=state["top_k"],
        language=target_language,
    )
    steps = list(state.get("steps_completed", []))
    steps.append("retrieve_primary")
    return {
        "hits": hits,
        "retrieval_language": target_language,
        "retrieval_pass": "primary",
        "steps_completed": steps,
    }


def translate_fallback_query_node(state: QAState) -> dict:
    """Translate the query for a fallback search in the other language."""
    query = _search_query(state)
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


def retrieve_fallback_node(state: QAState) -> dict:
    """Run hybrid retrieval scoped to the fallback language."""
    search_query = state.get("fallback_search_query") or _search_query(state)
    fallback_language = state["fallback_language"]
    hits = state["retriever"].search(
        search_query,
        top_k=state["top_k"],
        language=fallback_language,
    )
    steps = list(state.get("steps_completed", []))
    steps.append("retrieve_fallback")
    return {
        "hits": hits,
        "retrieval_language": fallback_language,
        "retrieval_pass": "fallback",
        "steps_completed": steps,
    }


def rerank_node(state: QAState) -> dict:
    """Rescore retrieved hits with the Cohere rerank API."""
    search_query = _rerank_search_query(state)
    reranked = rerank(
        search_query,
        state.get("hits", []),
        top_n=state["rerank_top_n"],
        settings=state["settings"],
        language=_rerank_language_boost(state),
    )
    steps = list(state.get("steps_completed", []))
    steps.append("rerank")
    return {"reranked": reranked, "steps_completed": steps}


def is_relevant_context(state: QAState) -> bool:
    """Return True when reranked hits meet the relevance threshold."""
    reranked = state.get("reranked", [])
    if not reranked:
        return False
    threshold = state["settings"].rerank_relevance_threshold
    top_score = max(hit.get("rerank_score", 0.0) for hit in reranked)
    return top_score >= threshold


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
        _search_query(state),
        state.get("reranked", []),
        settings=state["settings"],
        language=state.get("language"),
        context_language=state.get("retrieval_language"),
    )
    steps = list(state.get("steps_completed", []))
    steps.append("generate_answer")
    return {"answer": answer, "steps_completed": steps}


def is_off_topic_answer(answer: str) -> bool:
    """Return True when the answer is a canned or deflecting off-topic reply."""
    normalized = answer.strip()
    if not normalized:
        return True

    if normalized in _FALLBACK_MESSAGES.values():
        return True

    lowered = normalized.lower()
    return any(marker in lowered for marker in _OFF_TOPIC_MARKERS)


def extract_cited_sources(answer: str, reranked: list[dict]) -> list[Source]:
    """Keep only reranked sources explicitly cited in the answer."""
    if is_off_topic_answer(answer):
        return []

    cited_indices: list[int] = []
    for match in _CITATION_RE.findall(answer):
        index = int(match)
        if 1 <= index <= len(reranked) and index not in cited_indices:
            cited_indices.append(index)

    if not cited_indices:
        return []

    return [_to_source(reranked[index - 1]) for index in cited_indices]


def citations_node(state: QAState) -> dict:
    """Keep only the reranked sources actually cited by the answer."""
    reranked = state.get("reranked", [])
    answer = state.get("answer", "")
    sources = extract_cited_sources(answer, reranked)

    steps = list(state.get("steps_completed", []))
    steps.append("citations")
    return {"sources": sources, "steps_completed": steps}


def validation_node(state: QAState) -> dict:
    """Validate answer groundedness/citations and track retry attempts."""
    passed = validate_answer(
        _search_query(state),
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
