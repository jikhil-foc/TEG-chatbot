"""Citation parsing and off-topic answer detection."""

from __future__ import annotations

import re

from app.nodes.shared.canned_responses import FALLBACK_MESSAGES, OFF_TOPIC_MARKERS
from app.nodes.shared.retrieval_hit_mapper import to_source
from app.models.answer_types import Source

_CITATION_RE = re.compile(r"\[(\d+)\]")


def is_off_topic_answer(answer: str) -> bool:
    """Return True when the answer is empty or matches a canned fallback phrase."""
    normalized = answer.strip()
    if not normalized:
        return True
    if normalized in FALLBACK_MESSAGES.values():
        return True
    lowered = normalized.lower()
    return any(marker in lowered for marker in OFF_TOPIC_MARKERS)


def extract_cited_sources(answer: str, reranked: list[dict]) -> list[Source]:
    """Parse ``[n]`` citations in the answer and map them to ``Source`` objects.

    Returns an empty list for off-topic answers or when no valid citation
    indices appear, so the API never surfaces sources for generic fallbacks.
    """
    if is_off_topic_answer(answer):
        return []

    cited_indices: list[int] = []
    for match in _CITATION_RE.findall(answer):
        index = int(match)
        if 1 <= index <= len(reranked) and index not in cited_indices:
            cited_indices.append(index)

    if not cited_indices:
        return []

    return [to_source(reranked[index - 1]) for index in cited_indices]
