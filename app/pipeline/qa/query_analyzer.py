"""Analyze conversational queries for completeness and rewrite follow-ups."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage

from app.pipeline.embedding.config import EmbeddingSettings, get_embedding_settings
from app.pipeline.llm.chat_model import build_chat_model
from app.pipeline.qa.conversation import ConversationMessage
from app.pipeline.qa.session import (
    PendingClarification,
    clear_pending,
    get_pending,
    set_pending,
)

logger = logging.getLogger(__name__)

_AMBIGUOUS_FEE_RE = re.compile(
    r"\b(exam\s*)?fee?s?\b|\b(cost|price|how\s+much)\b",
    re.IGNORECASE,
)
_EXAM_TYPE_HINT_RE = re.compile(
    r"\b("
    r"secondary(?:\s+school)?|primary(?:\s+school)?|pupil|student|adult|"
    r"junior|senior|teg\s+level|level\s+[abc][12]?|"
    r"a[12]|b[12]|c[12]"
    r")\b",
    re.IGNORECASE,
)
_NEW_QUESTION_RE = re.compile(
    r"^(what|how|when|where|why|who|can|could|is|are|do|does|tell\s+me)\b",
    re.IGNORECASE,
)
_TEG_TOPIC_RE = re.compile(
    r"\b("
    r"teg|gaeilge|irish(?:\s+language)?|scr[uú]d[uú]|certification|"
    r"examination|exam(?:\s+fee)?s?|pupil|candidate|registration|"
    r"syllabus|accreditation|level\s+[abc][12]?|a[12]|b[12]|c[12]"
    r")\b",
    re.IGNORECASE,
)
_OFF_TOPIC_ENTITY_RE = re.compile(
    r"\b("
    r"dlf|apple|google|microsoft|tesla|amazon|facebook|meta|netflix|"
    r"bitcoin|ethereum|cricket|football|soccer|nba|nfl|premier\s+league"
    r")\b",
    re.IGNORECASE,
)
_OFF_TOPIC_PATTERN_RE = re.compile(
    r"\b(owner|ceo|founder|chairman|director)\s+of\b|"
    r"\bweather\b|\btemperature\b|"
    r"\b(cricket|football|soccer)\s+(score|match|result)\b|"
    r"\b(recipe|cook|bake)\s+",
    re.IGNORECASE,
)

_DEFAULT_CLARIFICATION = (
    "For which exam or candidate group are you asking about fees? "
    "For example, secondary school pupils, adults, or a specific TEG level."
)

_ANALYZE_SYSTEM_PROMPT = (
    "You analyze user questions for the TEG (Irish language exams) chatbot. "
    "TEG topics include: Irish language exams, certification levels (A1-C2), "
    "exam fees, registration, syllabi, candidate groups, and TEG services. "
    "Given the conversation history and the latest user message, classify the "
    "question as one of:\n"
    "- off_topic: unrelated to TEG (e.g. other companies, sports, weather, "
    "general knowledge)\n"
    "- needs_clarification: on-topic but missing key details (e.g. which exam "
    "or candidate group for fees)\n"
    "- complete: on-topic and specific enough to search the knowledge base\n"
    "Reply with JSON only, no markdown:\n"
    '{"status":"complete"|"needs_clarification"|"off_topic",'
    '"standalone_query":"self-contained search query when complete",'
    '"clarification_question":"question to ask when needs_clarification",'
    '"intent":"short topic label",'
    '"missing_slots":["slot names"]}'
)


@dataclass(frozen=True)
class QueryAnalysisResult:
    """Outcome of conversational query analysis."""

    status: Literal["complete", "needs_clarification", "off_topic"]
    effective_query: str
    clarification_question: str | None = None
    intent: str = ""
    missing_slots: tuple[str, ...] = ()


def _format_history(messages: list[ConversationMessage]) -> str:
    if not messages:
        return "(no prior messages)"
    lines: list[str] = []
    for message in messages[-8:]:
        role = "User" if message.role == "user" else "Assistant"
        lines.append(f"{role}: {message.content}")
    return "\n".join(lines)


def _looks_like_new_question(text: str) -> bool:
    stripped = text.strip()
    if len(stripped.split()) > 10:
        return True
    return bool(_NEW_QUESTION_RE.match(stripped))


def _mentions_teg_topic(query: str) -> bool:
    return bool(_TEG_TOPIC_RE.search(query))


def _is_likely_off_topic_query(query: str) -> bool:
    """Fast heuristic for clearly unrelated questions."""
    if _mentions_teg_topic(query):
        return False
    if _OFF_TOPIC_ENTITY_RE.search(query):
        return True
    if _OFF_TOPIC_PATTERN_RE.search(query):
        return True
    return False


def _is_likely_ambiguous_fee_query(query: str) -> bool:
    stripped = query.strip()
    if not _AMBIGUOUS_FEE_RE.search(stripped):
        return False
    if _EXAM_TYPE_HINT_RE.search(stripped):
        return False
    return True


def _merge_follow_up(pending: PendingClarification, reply: str) -> str:
    partial = pending.partial_query.rstrip("?.! ").strip()
    detail = reply.strip().rstrip("?.! ").strip()
    if not partial:
        return detail
    if not detail:
        return partial
    return f"{partial} for {detail}"


def _heuristic_off_topic(query: str) -> QueryAnalysisResult | None:
    if not _is_likely_off_topic_query(query):
        return None
    return QueryAnalysisResult(status="off_topic", effective_query=query)


def _heuristic_ambiguous_fee(query: str) -> QueryAnalysisResult | None:
    """Fast path for common ambiguous fee questions."""
    if not _is_likely_ambiguous_fee_query(query):
        return None

    return QueryAnalysisResult(
        status="needs_clarification",
        effective_query=query,
        clarification_question=_DEFAULT_CLARIFICATION,
        intent="exam_fees",
        missing_slots=("exam_type",),
    )


def _parse_llm_analysis(raw: str, fallback_query: str) -> QueryAnalysisResult:
    try:
        payload = json.loads(raw.strip())
    except json.JSONDecodeError:
        logger.warning("Failed to parse query analysis JSON: %r", raw[:200])
        return QueryAnalysisResult(status="complete", effective_query=fallback_query)

    status = payload.get("status", "complete")
    if status not in {"complete", "needs_clarification", "off_topic"}:
        status = "complete"

    standalone = str(payload.get("standalone_query") or fallback_query).strip()
    if not standalone:
        standalone = fallback_query

    if status == "off_topic":
        return QueryAnalysisResult(status="off_topic", effective_query=fallback_query)

    clarification = payload.get("clarification_question")
    if status == "needs_clarification":
        clarification = str(clarification or _DEFAULT_CLARIFICATION).strip()
        return QueryAnalysisResult(
            status="needs_clarification",
            effective_query=fallback_query,
            clarification_question=clarification,
            intent=str(payload.get("intent") or ""),
            missing_slots=tuple(payload.get("missing_slots") or ()),
        )

    return QueryAnalysisResult(
        status="complete",
        effective_query=standalone,
        intent=str(payload.get("intent") or ""),
    )


def _llm_analysis(
    query: str,
    messages: list[ConversationMessage],
    settings: EmbeddingSettings,
) -> QueryAnalysisResult:
    if not settings.openai_api_key:
        return QueryAnalysisResult(status="complete", effective_query=query)

    history = _format_history(messages)
    prompt = (
        f"Conversation history:\n{history}\n\n"
        f"Latest user message:\n{query}\n\n"
        "If the latest message is a short follow-up that answers a prior "
        "clarifying question, merge it into a complete standalone_query. "
        "Mark off_topic only when the question is clearly unrelated to TEG."
    )

    model = build_chat_model(settings)
    response = model.invoke(
        [
            SystemMessage(content=_ANALYZE_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
    )
    return _parse_llm_analysis(str(response.content), query)


def _store_pending_clarification(
    session_id: str | None,
    query: str,
    result: QueryAnalysisResult,
) -> None:
    if not session_id:
        return
    set_pending(
        session_id,
        PendingClarification(
            partial_query=query,
            intent=result.intent,
            missing_slots=list(result.missing_slots),
        ),
    )


def analyze_conversation(
    query: str,
    messages: list[ConversationMessage] | None = None,
    session_id: str | None = None,
    settings: EmbeddingSettings | None = None,
) -> QueryAnalysisResult:
    """Return whether to clarify, reject, or proceed with an effective query."""
    settings = settings or get_embedding_settings()
    messages = messages or []
    stripped = query.strip()

    pending = get_pending(session_id)
    if pending:
        if _looks_like_new_question(stripped):
            clear_pending(session_id)
            off_topic = _heuristic_off_topic(stripped)
            if off_topic is not None:
                logger.info("Off-topic new question after pending session: %r", stripped)
                return off_topic
        else:
            effective = _merge_follow_up(pending, stripped)
            clear_pending(session_id)
            logger.info(
                "Resolved follow-up for session %r: %r -> %r",
                session_id,
                stripped,
                effective,
            )
            return QueryAnalysisResult(
                status="complete",
                effective_query=effective,
                intent=pending.intent,
            )

    off_topic = _heuristic_off_topic(stripped)
    if off_topic is not None:
        clear_pending(session_id)
        logger.info("Heuristic off-topic query: %r", stripped)
        return off_topic

    ambiguous = _heuristic_ambiguous_fee(stripped)
    if ambiguous is not None:
        _store_pending_clarification(session_id, stripped, ambiguous)
        return ambiguous

    if not _mentions_teg_topic(stripped) and settings.openai_api_key:
        result = _llm_analysis(stripped, messages, settings)
        if result.status == "off_topic":
            clear_pending(session_id)
            logger.info("LLM off-topic query: %r", stripped)
            return result
        if result.status == "needs_clarification":
            _store_pending_clarification(session_id, stripped, result)
            return result
        return result

    if messages and settings.openai_api_key:
        result = _llm_analysis(stripped, messages, settings)
        if result.status == "off_topic":
            clear_pending(session_id)
            return result
        if result.status == "needs_clarification":
            _store_pending_clarification(session_id, stripped, result)
            return result
        return result

    return QueryAnalysisResult(status="complete", effective_query=stripped)
