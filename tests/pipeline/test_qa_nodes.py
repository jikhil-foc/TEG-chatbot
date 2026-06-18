"""Tests for QA citation and off-topic handling."""

from app.nodes.shared.citation_parser import extract_cited_sources, is_off_topic_answer
from app.nodes.retrieval import greeting_node


def test_greeting_node_returns_welcome_message() -> None:
    result = greeting_node(
        {
            "query": "Hi",
            "language": "English",
            "greeting_kind": "hello",
            "steps_completed": [],
        }
    )

    assert "TEG" in result["answer"]
    assert result["sources"] == []
    assert result["greeting"] is True
    assert result["off_topic"] is False


def test_is_off_topic_answer_detects_fallback_messages() -> None:
    assert is_off_topic_answer(
        "Please ask questions related to TEG. I'm here to help with TEG website content."
    )
    assert is_off_topic_answer(
        "Cuir ceist a bhaineann le TEG, le do thoil. Tá mé anseo chun cabhrú le hábhar láithreán TEG."
    )
    assert not is_off_topic_answer("TEG offers Irish language exams at several levels [1].")


def test_extract_cited_sources_empty_for_off_topic_answer() -> None:
    reranked = [
        {
            "chunk_id": "chunk-1",
            "score": 0.8,
            "rerank_score": 0.7,
            "metadata": {"url": "https://www.teg.ie/", "title": "Home"},
        }
    ]

    sources = extract_cited_sources(
        "Please ask questions related to TEG. I'm here to help with TEG website content.",
        reranked,
    )

    assert sources == []


def test_extract_cited_sources_only_returns_cited_hits() -> None:
    reranked = [
        {
            "chunk_id": "chunk-1",
            "score": 0.8,
            "rerank_score": 0.7,
            "metadata": {"url": "https://www.teg.ie/a", "title": "A"},
        },
        {
            "chunk_id": "chunk-2",
            "score": 0.6,
            "rerank_score": 0.5,
            "metadata": {"url": "https://www.teg.ie/b", "title": "B"},
        },
    ]

    sources = extract_cited_sources("TEG runs exams at multiple levels [2].", reranked)

    assert len(sources) == 1
    assert sources[0].chunk_id == "chunk-2"
    assert sources[0].url == "https://www.teg.ie/b"


def test_extract_cited_sources_empty_when_answer_has_no_citations() -> None:
    reranked = [
        {
            "chunk_id": "chunk-1",
            "score": 0.8,
            "rerank_score": 0.7,
            "metadata": {"url": "https://www.teg.ie/", "title": "Home"},
        }
    ]

    assert extract_cited_sources("TEG offers Irish language exams.", reranked) == []
