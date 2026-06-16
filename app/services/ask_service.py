"""Service orchestration for question answering."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx
from langsmith import traceable
from qdrant_client.http.exceptions import ResponseHandlingException

from app.pipeline.embedding.cache import get_retriever
from app.pipeline.embedding.config import get_embedding_settings
from app.pipeline.llm.models import AnswerResult
from app.pipeline.llm.pipeline import answer_question
from app.pipeline.qa.streaming import stream_qa_pipeline


class QdrantUnavailableError(ConnectionError):
    """Raised when the Qdrant vector database cannot be reached."""


def _qdrant_connection_message() -> str:
    url = get_embedding_settings().qdrant_url
    return (
        f"Cannot connect to Qdrant at {url}. "
        "Start Qdrant with: docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant"
    )


@traceable(run_type="chain", name="ask_service.answer")
def answer(query: str, top_k: int, rerank_top_n: int) -> AnswerResult:
    """Build the retriever and answer a question.

    Synchronous and CPU/IO-bound; call from a worker thread in async routes.
    Raises ``FileNotFoundError`` when the index has not been built yet.
    """
    retriever = get_retriever()
    return answer_question(query, top_k, rerank_top_n, retriever)


def ensure_index() -> None:
    """Verify the retrieval index exists before starting a stream."""
    try:
        get_retriever()
    except FileNotFoundError:
        raise
    except (httpx.ConnectError, ResponseHandlingException, ConnectionError) as exc:
        raise QdrantUnavailableError(_qdrant_connection_message()) from exc


@traceable(run_type="chain", name="ask_service.answer_stream")
def answer_stream(
    query: str,
    top_k: int,
    rerank_top_n: int,
) -> Iterator[dict[str, Any]]:
    """Stream QA events for Server-Sent Events clients.

    Raises ``FileNotFoundError`` when the index has not been built yet.
    """
    retriever = get_retriever()
    yield from stream_qa_pipeline(query, top_k, rerank_top_n, retriever)
