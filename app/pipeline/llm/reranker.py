"""Reranking via the Cohere Rerank API.

Rescues retrieval precision by rescoring each candidate against the query,
then reordering by relevance. The Cohere client is cached as a module-level
singleton keyed by API key.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.pipeline.crawl.text import detect_language_from_text
from app.pipeline.embedding.config import EmbeddingSettings, get_embedding_settings

if TYPE_CHECKING:
    import cohere

logger = logging.getLogger(__name__)

_client: "cohere.Client | None" = None
_client_api_key: str | None = None


def _get_client(api_key: str) -> "cohere.Client":
    """Lazily build and cache the Cohere client for the given API key."""
    global _client, _client_api_key
    if _client is None or _client_api_key != api_key:
        import cohere

        logger.info("Initializing Cohere rerank client")
        _client = cohere.Client(api_key=api_key)
        _client_api_key = api_key
    return _client


def _chunk_content_language(hit: dict) -> str | None:
    """Detect Irish vs English from passage text, with metadata fallback."""
    content = hit.get("content", "") or ""
    detected = detect_language_from_text(content)
    if detected:
        return detected
    metadata = hit.get("metadata") or {}
    return metadata.get("language")


def _apply_language_boost(
    scored: list[dict],
    language: str | None,
    boost: float,
) -> list[dict]:
    """Add ``boost`` to ``rerank_score`` when chunk language matches the query."""
    if language not in ("English", "Irish") or boost <= 0:
        return scored

    boosted: list[dict] = []
    for hit in scored:
        adjusted = dict(hit)
        if _chunk_content_language(hit) == language:
            adjusted["rerank_score"] = float(hit["rerank_score"]) + boost
        boosted.append(adjusted)

    boosted.sort(key=lambda item: item["rerank_score"], reverse=True)
    return boosted


def rerank(
    query: str,
    results: list[dict],
    top_n: int = 5,
    settings: EmbeddingSettings | None = None,
    language: str | None = None,
) -> list[dict]:
    """Rerank ``results`` against ``query`` and return the top ``top_n`` hits.

    ``results`` are dicts in the retriever contract shape
    (``{"chunk_id", "score", "content", "metadata"}``). Each returned hit gains
    a ``rerank_score`` field holding the Cohere relevance score (plus an optional
    language-match boost), and the list is sorted by that score in descending
    order.
    """
    if not results:
        return []

    settings = settings or get_embedding_settings()
    if not settings.cohere_api_key:
        raise ValueError(
            "COHERE_API_KEY is required for reranking. Set it in the environment "
            "or .env file."
        )

    documents = [{"text": result.get("content", "")} for result in results]
    client = _get_client(settings.cohere_api_key)

    logger.info(
        "Reranking %d candidates with %s (top_n=%d, language=%r)",
        len(documents),
        settings.cohere_rerank_model,
        top_n,
        language,
    )
    response = client.rerank(
        query=query,
        documents=documents,
        model=settings.cohere_rerank_model,
        top_n=len(results),
    )

    scored = [
        {**results[result.index], "rerank_score": float(result.relevance_score)}
        for result in response.results
    ]
    scored = _apply_language_boost(
        scored,
        language,
        settings.rerank_language_boost,
    )
    return scored[:top_n]
