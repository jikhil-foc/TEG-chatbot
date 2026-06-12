"""Cross-encoder reranking with ``BAAI/bge-reranker-v2-m3``.

Rescues retrieval precision by rescoring each candidate against the query with
a cross-encoder (which reads the query and passage jointly), then reordering.
The model is loaded lazily and cached as a module-level singleton because
loading/downloading it is expensive and it can be reused across requests.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
_MAX_LENGTH = 512

_reranker: "CrossEncoder | None" = None


def _get_reranker() -> "CrossEncoder":
    """Lazily build and cache the cross-encoder reranker (CPU)."""
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder

        logger.info("Loading cross-encoder reranker: %s (cpu)", RERANKER_MODEL)
        _reranker = CrossEncoder(
            RERANKER_MODEL,
            device="cpu",
            max_length=_MAX_LENGTH,
        )
    return _reranker


def rerank(query: str, results: list[dict], top_n: int = 5) -> list[dict]:
    """Rerank ``results`` against ``query`` and return the top ``top_n`` hits.

    ``results`` are dicts in the retriever contract shape
    (``{"chunk_id", "score", "content", "metadata"}``). Each returned hit gains
    a ``rerank_score`` field holding the cross-encoder relevance score, and the
    list is sorted by that score in descending order.
    """
    if not results:
        return []

    pairs = [(query, result.get("content", "")) for result in results]
    scores = _get_reranker().predict(pairs)

    scored = [
        {**result, "rerank_score": float(score)}
        for result, score in zip(results, scores)
    ]
    scored.sort(key=lambda result: result["rerank_score"], reverse=True)
    return scored[:top_n]
