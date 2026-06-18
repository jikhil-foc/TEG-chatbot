"""Grounded answer generation from reranked retrieval context.

Builds a numbered context block from reranked hits and prompts
``gpt-4o-mini`` to answer using only that context, citing sources as ``[n]``.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator

from langchain_core.messages import HumanMessage, SystemMessage

from app.config.embedding_settings import EmbeddingSettings, get_embedding_settings
from app.prompts.teg_assistant_system import SYSTEM_PROMPT
from app.services.openai_chat import build_chat_model

logger = logging.getLogger(__name__)


def _language_instruction(
    language: str | None,
    context_language: str | None = None,
) -> str:
    """Build a system instruction asking the model to reply in ``language``."""
    if not language:
        return ""
    instruction = f" Respond in {language}."
    if context_language and context_language != language:
        instruction += (
            f" The provided context is in {context_language}; convey all facts "
            f"in {language} in your answer."
        )
    return instruction


def build_context(reranked: list[dict]) -> str:
    """Render reranked hits into a numbered, citable context block."""
    blocks: list[str] = []
    for index, hit in enumerate(reranked, start=1):
        metadata = hit.get("metadata") or {}
        title = metadata.get("title", "") or "Untitled"
        url = metadata.get("url", "")
        content = (hit.get("content") or "").strip()
        header = f"[{index}] {title}"
        if url:
            header = f"{header} ({url})"
        blocks.append(f"{header}\n{content}")
    return "\n\n".join(blocks)


def generate_answer(
    query: str,
    reranked: list[dict],
    settings: EmbeddingSettings | None = None,
    language: str | None = None,
    context_language: str | None = None,
) -> str:
    """Generate a grounded answer to ``query`` from the ``reranked`` context.

    When ``language`` is provided the model is instructed to reply in that
    language (e.g. ``"Irish"`` or ``"English"``). When ``context_language``
    differs from ``language``, the model is told to translate facts from the
    retrieved context.
    """
    if not reranked:
        return (
            "Please ask questions related to TEG. "
            "I'm here to help with TEG website content."
        )

    settings = settings or get_embedding_settings()
    context = build_context(reranked)

    messages = [
        SystemMessage(
            content=SYSTEM_PROMPT
            + _language_instruction(language, context_language)
        ),
        HumanMessage(content=f"Context:\n{context}\n\nQuestion: {query}"),
    ]

    logger.info("Generating answer over %d reranked sources", len(reranked))
    model = build_chat_model(settings)
    response = model.invoke(messages)
    return str(response.content).strip()


def _chunk_content(chunk_content: object) -> str:
    """Normalise streamed model chunks to plain text."""
    if isinstance(chunk_content, str):
        return chunk_content
    if isinstance(chunk_content, list):
        parts: list[str] = []
        for block in chunk_content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "".join(parts)
    return str(chunk_content) if chunk_content else ""


def generate_answer_stream(
    query: str,
    reranked: list[dict],
    settings: EmbeddingSettings | None = None,
    language: str | None = None,
    context_language: str | None = None,
) -> Iterator[str]:
    """Stream a grounded answer token-by-token from the ``reranked`` context."""
    if not reranked:
        yield (
            "Please ask questions related to TEG. "
            "I'm here to help with TEG website content."
        )
        return

    settings = settings or get_embedding_settings()
    context = build_context(reranked)

    messages = [
        SystemMessage(
            content=SYSTEM_PROMPT
            + _language_instruction(language, context_language)
        ),
        HumanMessage(content=f"Context:\n{context}\n\nQuestion: {query}"),
    ]

    logger.info("Streaming answer over %d reranked sources", len(reranked))
    model = build_chat_model(settings)
    for chunk in model.stream(messages):
        text = _chunk_content(chunk.content)
        if text:
            yield text
