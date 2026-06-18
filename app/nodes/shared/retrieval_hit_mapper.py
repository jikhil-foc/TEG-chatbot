"""Map reranked retrieval hits to Source models."""

from __future__ import annotations

from app.models.answer_types import Source


def to_source(hit: dict) -> Source:
    metadata = hit.get("metadata") or {}
    return Source(
        chunk_id=hit.get("chunk_id", ""),
        url=metadata.get("url", ""),
        title=metadata.get("title", ""),
        score=float(hit.get("score", 0.0)),
        rerank_score=float(hit.get("rerank_score", 0.0)),
    )
