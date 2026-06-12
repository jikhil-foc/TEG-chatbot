"""Question-answering orchestrator: retrieve -> rerank -> answer.

Ties together the hybrid retriever, the cross-encoder reranker, and the
``gpt-4o-mini`` answer model into a single :func:`answer_question` call.
"""

from __future__ import annotations

import logging

from app.pipeline.embedding.config import EmbeddingSettings, get_embedding_settings
from app.pipeline.embedding.retriever import HybridRetriever
from app.pipeline.llm.answerer import generate_answer
from app.pipeline.llm.models import AnswerResult, Source
from app.pipeline.llm.reranker import rerank

logger = logging.getLogger(__name__)


def _to_source(hit: dict) -> Source:
    metadata = hit.get("metadata") or {}
    return Source(
        chunk_id=hit.get("chunk_id", ""),
        url=metadata.get("url", ""),
        title=metadata.get("title", ""),
        score=float(hit.get("score", 0.0)),
        rerank_score=float(hit.get("rerank_score", 0.0)),
    )


def answer_question(
    query: str,
    top_k: int = 10,
    rerank_top_n: int = 5,
    retriever: HybridRetriever | None = None,
    settings: EmbeddingSettings | None = None,
) -> AnswerResult:
    """Answer ``query`` end-to-end over the indexed corpus.

    Retrieves ``top_k`` hybrid-search hits, reranks them with the cross-encoder
    keeping the top ``rerank_top_n``, then generates a grounded, cited answer.
    """
    settings = settings or get_embedding_settings()
    retriever = retriever or HybridRetriever.from_settings(settings)

    logger.info("Answering query (top_k=%d, rerank_top_n=%d): %r", top_k, rerank_top_n, query)
    hits = retriever.search(query, top_k=top_k)
    reranked = rerank(query, hits, top_n=rerank_top_n)
    answer = generate_answer(query, reranked, settings=settings)

    return AnswerResult(
        answer=answer,
        sources=[_to_source(hit) for hit in reranked],
    )
