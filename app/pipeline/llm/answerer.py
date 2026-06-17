"""Grounded answer generation from reranked retrieval context.

Builds a numbered context block from reranked hits and prompts
``gpt-4o-mini`` to answer using only that context, citing sources as ``[n]``.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator

from langchain_core.messages import HumanMessage, SystemMessage

from app.pipeline.embedding.config import EmbeddingSettings, get_embedding_settings
from app.pipeline.llm.chat_model import build_chat_model

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a helpful assistant for the TEG website. Answer the user's "
    "question using ONLY the information in the provided context. Be concise "
    "and accurate. Cite the sources you use inline with bracketed numbers that "
    "match the context, e.g. [1] or [2][3]. If the context contains multiple "
    "different exam types, candidate groups, or fee tables, answer only for the "
    "group the user asked about. If the user's question is too vague to know "
    "which group applies, ask a specific clarifying question instead of "
    "combining conflicting details. If the context does not contain enough "
    "information to answer, politely ask the user to ask a question related "
    "to TEG. Do not invent facts or cite sources not provided.\n\n"
    "Format your answer in Markdown for readability:\n"
    "- Use short paragraphs for prose.\n"
    "- Use bullet or numbered lists for steps, requirements, or multiple items.\n"
    "- Use **bold** for key terms such as exam names, dates, and fees.\n"
    "- Use Markdown tables when presenting structured data (fees, dates, levels).\n"
    "- Keep inline source citations as [1], [2], etc. Do not use markdown links "
    "for citations.\n"
    "Do not wrap the entire answer in a code fence."
)


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


def _build_context(reranked: list[dict]) -> str:
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
    context = _build_context(reranked)

    messages = [
        SystemMessage(
            content=_SYSTEM_PROMPT
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
    context = _build_context(reranked)

    messages = [
        SystemMessage(
            content=_SYSTEM_PROMPT
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
