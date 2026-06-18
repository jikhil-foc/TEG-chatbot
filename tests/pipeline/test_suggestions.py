"""Tests for related question suggestion generation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.config.embedding_settings import EmbeddingSettings
from app.qa.sse_event_stream import _done_event, _should_generate_related_questions
from app.qa.related_question_generator import generate_related_questions


def _settings_with_key() -> EmbeddingSettings:
    return EmbeddingSettings(openai_api_key="test-key")


def test_generate_related_questions_parses_valid_json() -> None:
    mock_response = MagicMock()
    mock_response.content = (
        '{"questions":["What TEG levels are available?","How do I register?"]}'
    )
    mock_model = MagicMock()
    mock_model.invoke.return_value = mock_response

    with patch(
        "app.qa.related_question_generator.build_chat_model",
        return_value=mock_model,
    ):
        questions = generate_related_questions(
            "What are TEG exams?",
            "TEG offers Irish language certification exams.",
            settings=_settings_with_key(),
        )

    assert questions == [
        "What TEG levels are available?",
        "How do I register?",
    ]


def test_generate_related_questions_returns_empty_on_malformed_json() -> None:
    mock_response = MagicMock()
    mock_response.content = "not json"
    mock_model = MagicMock()
    mock_model.invoke.return_value = mock_response

    with patch(
        "app.qa.related_question_generator.build_chat_model",
        return_value=mock_model,
    ):
        questions = generate_related_questions(
            "What are TEG exams?",
            "TEG offers Irish language certification exams.",
            settings=_settings_with_key(),
        )

    assert questions == []


def test_generate_related_questions_returns_empty_without_api_key() -> None:
    questions = generate_related_questions(
        "What are TEG exams?",
        "TEG offers Irish language certification exams.",
        settings=EmbeddingSettings(openai_api_key=""),
    )

    assert questions == []


def test_should_generate_related_questions_skips_clarification() -> None:
    assert not _should_generate_related_questions(
        {"needs_clarification": True, "answer": "Which exam type?"}
    )


def test_should_generate_related_questions_skips_off_topic() -> None:
    assert not _should_generate_related_questions(
        {"off_topic": True, "answer": "Please ask TEG questions."}
    )


def test_should_generate_related_questions_skips_fallback() -> None:
    assert not _should_generate_related_questions(
        {"fallback": True, "answer": "Please ask TEG questions."}
    )


def test_done_event_includes_related_questions_for_normal_answer() -> None:
    with patch(
        "app.qa.sse_event_stream.generate_related_questions",
        return_value=["What are exam fees?", "How do I register?"],
    ):
        event = _done_event(
            "What are TEG levels?",
            {
                "answer": "TEG offers levels from A1 to C2.",
                "effective_query": "What are TEG levels?",
                "language": "English",
                "sources": [],
                "settings": _settings_with_key(),
            },
        )

    assert event["related_questions"] == [
        "What are exam fees?",
        "How do I register?",
    ]


def test_done_event_omits_related_questions_for_clarification() -> None:
    event = _done_event(
        "Exam fees",
        {
            "needs_clarification": True,
            "answer": "For which exam or candidate group are you asking about fees?",
            "settings": _settings_with_key(),
        },
    )

    assert event["related_questions"] == []
