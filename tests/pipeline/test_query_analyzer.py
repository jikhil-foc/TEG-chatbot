"""Tests for conversational query analysis and session handling."""

from app.pipeline.qa.query_analyzer import analyze_conversation
from app.pipeline.qa.session import get_pending, reset_sessions


def setup_function() -> None:
    reset_sessions()


def test_ambiguous_exam_fees_requests_clarification() -> None:
    result = analyze_conversation("Exam Fees", session_id="session-1")

    assert result.status == "needs_clarification"
    assert result.clarification_question
    assert "exam" in result.clarification_question.lower()

    pending = get_pending("session-1")
    assert pending is not None
    assert pending.partial_query == "Exam Fees"
    assert pending.intent == "exam_fees"


def test_specific_exam_fees_query_is_complete() -> None:
    result = analyze_conversation(
        "Exam fees for secondary school pupils",
        session_id="session-2",
    )

    assert result.status == "complete"
    assert result.effective_query == "Exam fees for secondary school pupils"
    assert get_pending("session-2") is None


def test_follow_up_resolves_pending_clarification() -> None:
    first = analyze_conversation("Exam fees", session_id="session-3")
    assert first.status == "needs_clarification"

    second = analyze_conversation(
        "Secondary school pupils",
        session_id="session-3",
    )

    assert second.status == "complete"
    assert second.effective_query == "Exam fees for Secondary school pupils"
    assert get_pending("session-3") is None


def test_new_question_clears_pending_clarification() -> None:
    analyze_conversation("Exam fees", session_id="session-4")
    assert get_pending("session-4") is not None

    result = analyze_conversation(
        "What services does TEG provide?",
        session_id="session-4",
    )

    assert result.status == "complete"
    assert result.effective_query == "What services does TEG provide?"
    assert get_pending("session-4") is None


def test_off_topic_dlf_owner_query() -> None:
    result = analyze_conversation("What is owner of DLF")

    assert result.status == "off_topic"
    assert result.effective_query == "What is owner of DLF"


def test_off_topic_weather_query() -> None:
    result = analyze_conversation("What is the weather in Dublin today?")

    assert result.status == "off_topic"


def test_teg_related_query_is_not_off_topic() -> None:
    result = analyze_conversation("What services does TEG provide?")

    assert result.status == "complete"
    assert result.effective_query == "What services does TEG provide?"
