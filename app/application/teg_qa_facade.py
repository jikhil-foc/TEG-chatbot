"""TEG question-answering application facade."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx
from langsmith import traceable
from qdrant_client.http.exceptions import ResponseHandlingException

from app.config.embedding_settings import EmbeddingSettings, get_embedding_settings
from app.models.answer_types import AnswerResult
from app.pipelines.retrieval.hybrid_retriever import HybridRetriever
from app.pipelines.retrieval.retriever_cache import get_retriever
from app.qa.conversation_history import ConversationMessage
from app.qa.sse_event_stream import stream_qa_pipeline


class QdrantUnavailableError(ConnectionError):
    """Raised when the Qdrant vector database cannot be reached."""


def _qdrant_connection_message() -> str:
    url = get_embedding_settings().qdrant_url
    return (
        f"Cannot connect to Qdrant at {url}. "
        "Start Qdrant with: docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant"
    )


def answer_question(
    query: str,
    top_k: int = 10,
    rerank_top_n: int = 5,
    retriever: HybridRetriever | None = None,
    settings: EmbeddingSettings | None = None,
    messages: list[ConversationMessage] | None = None,
    session_id: str | None = None,
) -> AnswerResult:
    from app.graphs.qa_rag_graph import run_qa_pipeline

    return run_qa_pipeline(
        query,
        top_k=top_k,
        rerank_top_n=rerank_top_n,
        retriever=retriever,
        settings=settings,
        messages=messages,
        session_id=session_id,
    )


@traceable(run_type="chain", name="ask_service.answer")
def answer(
    query: str,
    top_k: int,
    rerank_top_n: int,
    messages: list[ConversationMessage] | None = None,
    session_id: str | None = None,
) -> AnswerResult:
    retriever = get_retriever()
    return answer_question(
        query,
        top_k,
        rerank_top_n,
        retriever,
        messages=messages,
        session_id=session_id,
    )


def ensure_index() -> None:
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
    messages: list[ConversationMessage] | None = None,
    session_id: str | None = None,
) -> Iterator[dict[str, Any]]:
    retriever = get_retriever()
    yield from stream_qa_pipeline(
        query,
        top_k,
        rerank_top_n,
        retriever,
        messages=messages,
        session_id=session_id,
    )
