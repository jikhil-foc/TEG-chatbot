"""LLM validation agent for generated QA answers.

Checks that an answer is fully grounded in the numbered retrieval context and
only cites sources that exist, returning a simple pass/fail used by the QA
graph to decide whether to retry answer generation.
"""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.pipeline.embedding.config import EmbeddingSettings, get_embedding_settings
from app.pipeline.llm.answerer import _build_context
from app.pipeline.llm.chat_model import build_chat_model

logger = logging.getLogger(__name__)

_VALIDATION_SYSTEM_PROMPT = (
    "You are a strict answer validator for a retrieval-augmented assistant. "
    "You are given a question, a numbered context, and a candidate answer. "
    "Decide whether the answer is fully grounded in the context (no invented "
    "facts) and whether every bracketed citation like [1] or [2][3] refers to "
    "a number that exists in the context. Reply with exactly one word: PASS if "
    "the answer is grounded and its citations are valid, otherwise FAIL."
)


def validate_answer(
    query: str,
    answer: str,
    reranked: list[dict],
    settings: EmbeddingSettings | None = None,
) -> bool:
    """Return ``True`` when ``answer`` is grounded in ``reranked`` context.

    Uses ``gpt-4o-mini`` at ``temperature=0`` to judge groundedness and
    citation validity. An empty answer or empty context fails validation.
    """
    if not answer.strip() or not reranked:
        return False

    settings = settings or get_embedding_settings()
    context = _build_context(reranked)

    messages = [
        SystemMessage(content=_VALIDATION_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Context:\n{context}\n\nQuestion: {query}\n\n"
                f"Candidate answer:\n{answer}"
            )
        ),
    ]

    logger.info("Validating answer over %d reranked sources", len(reranked))
    model = build_chat_model(settings)
    response = model.invoke(messages)
    verdict = str(response.content).strip().upper()
    return verdict.startswith("PASS")
