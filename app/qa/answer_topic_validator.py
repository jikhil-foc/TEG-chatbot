"""LLM validation agent for generated QA answers.

Checks that an answer is fully grounded in the numbered retrieval context and
only cites sources that exist, returning a simple pass/fail used by the QA
graph to decide whether to retry answer generation.
"""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.config.embedding_settings import EmbeddingSettings, get_embedding_settings
from app.prompts.answer_validation import SYSTEM_PROMPT as VALIDATION_SYSTEM_PROMPT
from app.services.grounded_answer import build_context
from app.services.openai_chat import build_chat_model

logger = logging.getLogger(__name__)


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
    context = build_context(reranked)

    messages = [
        SystemMessage(content=VALIDATION_SYSTEM_PROMPT),
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
