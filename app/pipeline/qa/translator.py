"""Translate user queries for cross-lingual retrieval."""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.pipeline.embedding.config import EmbeddingSettings, get_embedding_settings
from app.pipeline.llm.chat_model import build_chat_model

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You translate user questions for the TEG (Irish language exams) chatbot "
    "search index. Translate faithfully for retrieval: preserve meaning, names, "
    "and TEG-specific terms. Return only the translated question with no "
    "explanation or quotation marks."
)


def translate_query(
    query: str,
    target_language: str,
    settings: EmbeddingSettings | None = None,
) -> str:
    """Translate ``query`` into ``target_language`` (``English`` or ``Irish``)."""
    stripped = (query or "").strip()
    if not stripped:
        return stripped

    settings = settings or get_embedding_settings()
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(
            content=f"Translate this question into {target_language}:\n\n{stripped}"
        ),
    ]

    try:
        model = build_chat_model(settings)
        response = model.invoke(messages)
        translated = str(response.content).strip()
        if translated:
            logger.info(
                "Translated query to %s: %r -> %r",
                target_language,
                stripped[:120],
                translated[:120],
            )
            return translated
    except Exception:
        logger.warning(
            "Query translation to %s failed; using original query",
            target_language,
            exc_info=True,
        )

    return stripped
