"""Grounded answer generation from reranked retrieval context.

Builds a numbered context block from reranked hits and prompts
``gpt-4o-mini`` to answer using only that context, citing sources as ``[n]``.
"""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.pipeline.embedding.config import EmbeddingSettings, get_embedding_settings
from app.pipeline.llm.chat_model import build_chat_model

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a helpful assistant for the TEG website. Answer the user's "
    "question using ONLY the information in the provided context. Be concise "
    "and accurate. Cite the sources you use inline with bracketed numbers that "
    "match the context, e.g. [1] or [2][3]. If the context does not contain "
    "enough information to answer, say that you don't know based on the "
    "available information. Do not invent facts or cite sources not provided."
)


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
) -> str:
    """Generate a grounded answer to ``query`` from the ``reranked`` context."""
    if not reranked:
        return "I don't know based on the available information."

    settings = settings or get_embedding_settings()
    context = _build_context(reranked)

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=f"Context:\n{context}\n\nQuestion: {query}"),
    ]

    logger.info("Generating answer over %d reranked sources", len(reranked))
    model = build_chat_model(settings)
    response = model.invoke(messages)
    return str(response.content).strip()
