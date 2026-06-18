"""Translate user queries for cross-lingual retrieval."""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.config.embedding_settings import EmbeddingSettings, get_embedding_settings
from app.prompts.en_ga_query_translation import SYSTEM_PROMPT
from app.services.openai_chat import build_chat_model

logger = logging.getLogger(__name__)


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
        SystemMessage(content=SYSTEM_PROMPT),
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
