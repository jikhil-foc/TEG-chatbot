"""Tests for graph node completion summaries."""

from __future__ import annotations

from app.graphs.node_completion_log import build_node_summary


def test_qa_detect_language_summary() -> None:
    summary = build_node_summary(
        "qa",
        "detect_language",
        {"language": "en", "fallback_language": "ga"},
    )
    assert "language=en" in summary
    assert "fallback=ga" in summary


def test_qa_rerank_summary_includes_top_score() -> None:
    summary = build_node_summary(
        "qa",
        "rerank",
        {
            "reranked": [
                {"rerank_score": 0.42},
                {"rerank_score": 0.91},
            ]
        },
    )
    assert "reranked=2" in summary
    assert "top_score=0.910" in summary


def test_ingestion_crawl_summary() -> None:
    summary = build_node_summary(
        "ingestion",
        "crawl",
        {"crawl_total": 10, "crawl_succeeded": 9, "crawl_failed": 1},
    )
    assert "total=10" in summary
    assert "succeeded=9" in summary
    assert "failed=1" in summary


def test_unknown_node_returns_completed() -> None:
    assert build_node_summary("qa", "unknown_node", {}) == "completed"
