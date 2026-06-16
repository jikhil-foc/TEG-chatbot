"""Streaming QA orchestration for Server-Sent Events responses."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from app.pipeline.crawl.text import detect_query_language
from app.pipeline.embedding.config import EmbeddingSettings, get_embedding_settings
from app.pipeline.embedding.retriever import HybridRetriever
from app.pipeline.llm.answerer import generate_answer_stream
from app.pipeline.llm.reranker import rerank
from app.pipeline.qa.nodes import extract_cited_sources, fallback_node

logger = logging.getLogger(__name__)

_DEFAULT_LANGUAGE = "English"


def _relevance_passes(reranked: list[dict], settings: EmbeddingSettings) -> bool:
    if not reranked:
        return False
    threshold = settings.rerank_relevance_threshold
    top_score = max(hit.get("rerank_score", 0.0) for hit in reranked)
    return top_score >= threshold


def stream_qa_pipeline(
    query: str,
    top_k: int,
    rerank_top_n: int,
    retriever: HybridRetriever,
    settings: EmbeddingSettings | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield SSE-friendly events through the QA pipeline with streamed generation."""
    settings = settings or get_embedding_settings()

    yield {"type": "status", "step": "detect_language"}
    language = detect_query_language(query) or _DEFAULT_LANGUAGE

    yield {"type": "status", "step": "retrieve"}
    hits = retriever.search(query, top_k=top_k)

    yield {"type": "status", "step": "rerank"}
    reranked = rerank(
        query,
        hits,
        top_n=rerank_top_n,
        settings=settings,
    )

    if not _relevance_passes(reranked, settings):
        fallback = fallback_node({"language": language, "steps_completed": []})
        answer = fallback["answer"]
        logger.info("Streaming fallback answer for low-relevance query: %r", query)
        yield {"type": "token", "content": answer}
        yield {
            "type": "done",
            "query": query,
            "answer": answer,
            "language": language,
            "sources": [],
        }
        return

    yield {"type": "status", "step": "generate"}
    answer_parts: list[str] = []
    for token in generate_answer_stream(
        query,
        reranked,
        settings=settings,
        language=language,
    ):
        answer_parts.append(token)
        yield {"type": "token", "content": token}

    answer = "".join(answer_parts).strip()
    sources = extract_cited_sources(answer, reranked)

    yield {
        "type": "done",
        "query": query,
        "answer": answer,
        "language": language,
        "sources": [source.model_dump() for source in sources],
    }
