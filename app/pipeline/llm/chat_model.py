"""Chat completion model backed by OpenAI.

Wraps :class:`langchain_openai.ChatOpenAI` with explicit configuration and
built-in retry on transient API failures, mirroring
:func:`app.pipeline.embedding.dense.build_dense_embeddings`.
"""

from __future__ import annotations

import logging

from langchain_openai import ChatOpenAI

from app.pipeline.embedding.config import EmbeddingSettings

logger = logging.getLogger(__name__)


def build_chat_model(
    settings: EmbeddingSettings,
    model: str | None = None,
) -> ChatOpenAI:
    """Construct a ``ChatOpenAI`` client from ``settings``.

    Uses ``temperature=0`` for deterministic, grounded answers and delegates
    retries to the underlying OpenAI client via ``max_retries``.
    """
    if not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY is not set. Add it to your environment or .env file."
        )

    resolved_model = model or settings.openai_chat_model
    logger.info("Initialising chat model: model=%s", resolved_model)
    return ChatOpenAI(
        model=resolved_model,
        api_key=settings.openai_api_key,
        temperature=0,
        max_retries=settings.max_retries,
        timeout=settings.qdrant_timeout,
    )