"""Application facades for API routes."""

from app.application.teg_ingest_facade import ingest
from app.application.teg_qa_facade import (
    QdrantUnavailableError,
    answer,
    answer_question,
    answer_stream,
    ensure_index,
)

__all__ = [
    "QdrantUnavailableError",
    "answer",
    "answer_question",
    "answer_stream",
    "ensure_index",
    "ingest",
]
