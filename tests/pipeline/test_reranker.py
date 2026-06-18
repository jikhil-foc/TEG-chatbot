"""Tests for Cohere reranking and language-match score boosts."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.config.embedding_settings import EmbeddingSettings
from app.services.cohere_reranker import _apply_language_boost, rerank


def _hit(chunk_id: str, content: str, *, language: str | None = None) -> dict:
    metadata = {"language": language} if language else {}
    return {
        "chunk_id": chunk_id,
        "score": 0.5,
        "content": content,
        "metadata": metadata,
    }


def test_apply_language_boost_adds_bonus_for_matching_english() -> None:
    scored = [
        {**_hit("en", "english"), "rerank_score": 0.6},
        {**_hit("ga", "irish"), "rerank_score": 0.7},
    ]

    with patch(
        "app.services.cohere_reranker._chunk_content_language",
        side_effect=["English", "Irish"],
    ):
        boosted = _apply_language_boost(scored, "English", 0.25)

    assert boosted[0]["chunk_id"] == "en"
    assert boosted[0]["rerank_score"] == 0.85
    assert boosted[1]["rerank_score"] == 0.7


def test_apply_language_boost_adds_bonus_for_matching_irish() -> None:
    scored = [
        {**_hit("en", "english"), "rerank_score": 0.8},
        {**_hit("ga", "irish"), "rerank_score": 0.56},
    ]

    with patch(
        "app.services.cohere_reranker._chunk_content_language",
        side_effect=["English", "Irish"],
    ):
        boosted = _apply_language_boost(scored, "Irish", 0.25)

    assert boosted[0]["chunk_id"] == "ga"
    assert boosted[0]["rerank_score"] == 0.81
    assert boosted[1]["rerank_score"] == 0.8


def test_apply_language_boost_skips_unknown_language() -> None:
    scored = [{**_hit("en", "english"), "rerank_score": 0.6}]

    with patch(
        "app.services.cohere_reranker._chunk_content_language",
        return_value="English",
    ):
        boosted = _apply_language_boost(scored, None, 0.25)

    assert boosted[0]["rerank_score"] == 0.6


@patch("app.services.cohere_reranker._get_client")
def test_rerank_scores_all_candidates_then_applies_language_boost(
    mock_get_client: MagicMock,
) -> None:
    hits = [
        _hit("a", "chunk a"),
        _hit("b", "chunk b"),
        _hit("c", "chunk c"),
    ]
    mock_get_client.return_value.rerank.return_value = SimpleNamespace(
        results=[
            SimpleNamespace(index=0, relevance_score=0.5),
            SimpleNamespace(index=1, relevance_score=0.9),
            SimpleNamespace(index=2, relevance_score=0.7),
        ]
    )
    settings = EmbeddingSettings(
        cohere_api_key="test-key",
        rerank_language_boost=0.25,
    )

    with patch(
        "app.services.cohere_reranker._chunk_content_language",
        side_effect=["Irish", "English", "Irish"],
    ):
        ranked = rerank(
            "test query",
            hits,
            top_n=2,
            settings=settings,
            language="Irish",
        )

    mock_get_client.return_value.rerank.assert_called_once()
    assert mock_get_client.return_value.rerank.call_args.kwargs["top_n"] == 3
    assert len(ranked) == 2
    assert ranked[0]["chunk_id"] == "c"
    assert ranked[0]["rerank_score"] == 0.95
    assert ranked[1]["chunk_id"] == "b"
    assert ranked[1]["rerank_score"] == 0.9
