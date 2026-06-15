"""Service orchestration for question answering."""

from __future__ import annotations

from app.pipeline.embedding.cache import get_retriever
from app.pipeline.llm.models import AnswerResult
from app.pipeline.llm.pipeline import answer_question


def answer(query: str, top_k: int, rerank_top_n: int) -> AnswerResult:
    """Build the retriever and answer a question.

    Synchronous and CPU/IO-bound; call from a worker thread in async routes.
    Raises ``FileNotFoundError`` when the index has not been built yet.
    """
    retriever = get_retriever()
    return answer_question(query, top_k, rerank_top_n, retriever)
