"""Generate related follow-up questions after a successful assistant answer."""

from __future__ import annotations

import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.pipeline.embedding.config import EmbeddingSettings, get_embedding_settings
from app.pipeline.llm.chat_model import build_chat_model

logger = logging.getLogger(__name__)

_MAX_QUESTIONS = 3
_MAX_QUESTION_LENGTH = 120

_SYSTEM_PROMPT = (
    "You suggest follow-up questions for the TEG (Irish language exams) chatbot. "
    "Given the user's question and the assistant's answer, propose 2–3 short "
    "questions a user might ask next. Questions must be about TEG topics: exams, "
    "certification levels (A1–C2), fees, registration, syllabi, candidate groups, "
    "and TEG services. Each question should be related to the conversation but "
    "must not repeat or closely paraphrase the original question or answer. "
    "Phrase each as a natural user question, under 80 characters when possible. "
    "Reply with JSON only, no markdown:\n"
    '{"questions":["question one","question two","question three"]}'
)


def _language_instruction(language: str | None) -> str:
    if not language:
        return ""
    return f" Write all questions in {language}."


def _parse_questions(raw: str) -> list[str]:
    try:
        payload = json.loads(raw.strip())
    except json.JSONDecodeError:
        logger.warning("Failed to parse related questions JSON: %r", raw[:200])
        return []

    questions = payload.get("questions")
    if not isinstance(questions, list):
        return []

    parsed: list[str] = []
    for item in questions:
        if not isinstance(item, str):
            continue
        text = re.sub(r"\s+", " ", item).strip()
        if not text:
            continue
        if len(text) > _MAX_QUESTION_LENGTH:
            text = text[:_MAX_QUESTION_LENGTH].rstrip()
        parsed.append(text)
        if len(parsed) >= _MAX_QUESTIONS:
            break
    return parsed


def generate_related_questions(
    query: str,
    answer: str,
    *,
    language: str | None = None,
    settings: EmbeddingSettings | None = None,
) -> list[str]:
    """Return 2–3 related follow-up questions, or an empty list on failure."""
    settings = settings or get_embedding_settings()
    if not settings.openai_api_key:
        return []

    stripped_answer = answer.strip()
    if not stripped_answer:
        return []

    prompt = (
        f"User question:\n{query.strip()}\n\n"
        f"Assistant answer:\n{stripped_answer}\n\n"
        "Suggest follow-up questions."
    )

    try:
        model = build_chat_model(settings)
        response = model.invoke(
            [
                SystemMessage(content=_SYSTEM_PROMPT + _language_instruction(language)),
                HumanMessage(content=prompt),
            ]
        )
        return _parse_questions(str(response.content))
    except Exception:
        logger.exception("Failed to generate related questions")
        return []
