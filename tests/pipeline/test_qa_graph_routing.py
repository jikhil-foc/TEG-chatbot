"""Tests for cross-lingual QA graph routing and retrieval nodes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.config.embedding_settings import EmbeddingSettings
from app.graphs.qa_rag_graph import (
    _route_after_fallback_rerank,
    _route_after_primary_rerank,
    _route_after_rerank,
)
from app.nodes.retrieval import (
    detect_language_node,
    retrieve_fallback_node,
    retrieve_primary_node,
    translate_fallback_query_node,
)


def _settings() -> EmbeddingSettings:
    return EmbeddingSettings(
        openai_api_key="test-key",
        cohere_api_key="test-key",
        rerank_relevance_threshold=0.5,
    )


def test_detect_language_node_sets_fallback_language() -> None:
    result = detect_language_node(
        {"query": "What services does TEG provide?", "steps_completed": []}
    )

    assert result["language"] == "English"
    assert result["fallback_language"] == "Irish"
    assert result["retrieval_language"] is None


def test_route_after_primary_rerank_passes_to_generate_answer() -> None:
    state = {
        "reranked": [{"rerank_score": 0.8}],
        "settings": _settings(),
    }

    assert _route_after_primary_rerank(state) == "generate_answer"


def test_route_after_primary_rerank_fails_to_translate_fallback() -> None:
    state = {
        "reranked": [{"rerank_score": 0.1}],
        "settings": _settings(),
    }

    assert _route_after_primary_rerank(state) == "translate_fallback_query"


def test_route_after_fallback_rerank_fails_to_canned_fallback() -> None:
    state = {
        "reranked": [],
        "settings": _settings(),
        "retrieval_pass": "fallback",
    }

    assert _route_after_fallback_rerank(state) == "fallback"


def test_route_after_rerank_uses_retrieval_pass() -> None:
    state_primary = {
        "reranked": [{"rerank_score": 0.1}],
        "settings": _settings(),
        "retrieval_pass": "primary",
    }
    state_fallback = {
        "reranked": [{"rerank_score": 0.8}],
        "settings": _settings(),
        "retrieval_pass": "fallback",
    }

    assert _route_after_rerank(state_primary) == "translate_fallback_query"
    assert _route_after_rerank(state_fallback) == "generate_answer"


@patch("app.nodes.retrieval.translate_query_for_fallback.translate_query", return_value="Cad iad na seirbhísí?")
def test_translate_fallback_query_node(mock_translate: MagicMock) -> None:
    result = translate_fallback_query_node(
        {
            "query": "What services does TEG provide?",
            "fallback_language": "Irish",
            "settings": _settings(),
            "steps_completed": [],
        }
    )

    assert result["fallback_search_query"] == "Cad iad na seirbhísí?"
    mock_translate.assert_called_once()


def test_retrieve_primary_node_filters_by_target_language() -> None:
    retriever = MagicMock()
    retriever.search.return_value = [{"chunk_id": "en-1"}]
    state = {
        "query": "What services does TEG provide?",
        "language": "English",
        "top_k": 10,
        "retriever": retriever,
        "steps_completed": [],
    }

    result = retrieve_primary_node(state)

    retriever.search.assert_called_once_with(
        "What services does TEG provide?",
        top_k=10,
        language="English",
    )
    assert result["retrieval_pass"] == "primary"
    assert result["retrieval_language"] == "English"


def test_retrieve_fallback_node_uses_translated_query() -> None:
    retriever = MagicMock()
    retriever.search.return_value = [{"chunk_id": "ga-1"}]
    state = {
        "query": "What services does TEG provide?",
        "fallback_language": "Irish",
        "fallback_search_query": "Cad iad na seirbhísí?",
        "top_k": 10,
        "retriever": retriever,
        "steps_completed": [],
    }

    result = retrieve_fallback_node(state)

    retriever.search.assert_called_once_with(
        "Cad iad na seirbhísí?",
        top_k=10,
        language="Irish",
    )
    assert result["retrieval_pass"] == "fallback"
    assert result["retrieval_language"] == "Irish"
