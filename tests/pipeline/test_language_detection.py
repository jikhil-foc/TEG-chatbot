"""Tests for Irish vs English query language detection."""

from __future__ import annotations

import pytest

from app.pipeline.crawl.text import detect_language_from_text, detect_query_language
from app.pipeline.language.utils import opposite_language


@pytest.mark.parametrize(
    "query",
    [
        "How do I submit a TEG appeal?",
        "What do I need for TEG?",
        "Where can I register for the exam?",
    ],
)
def test_detect_query_language_clear_english_questions(query: str) -> None:
    assert detect_query_language(query) == "English"


@pytest.mark.parametrize(
    "query",
    [
        "What is TEG?",
        "TEG certification levels",
    ],
)
def test_detect_query_language_ambiguous_english_not_irish(query: str) -> None:
    """Weak or stopword-free English defaults to None (English in the QA pipeline)."""
    assert detect_query_language(query) is None


@pytest.mark.parametrize(
    "query",
    [
        "Conas a dhéanaim iarratas ar achomharc?",
        "An bhfuil ceist agat faoi scrúdú TEG?",
        "Cá bhfuil na sonraí scrúdaithe?",
        "Cad iad na leibhéil deimhnithe TEG?",
    ],
)
def test_detect_query_language_irish_questions(query: str) -> None:
    assert detect_query_language(query) == "Irish"


def test_detect_query_language_single_weak_signal_defaults_to_none() -> None:
    """A lone ambiguous token should not force Irish on an English-looking query."""
    assert detect_query_language("Submit TEG go appeal") is None


def test_detect_language_from_text_unchanged_for_long_pages() -> None:
    """Page-level detection should not use the query margin rule."""
    english_page = " ".join(
        [
            "The TEG certification exam is available for candidates who want",
            "to demonstrate their Irish language skills at different levels.",
            "Registration opens in the spring and closes before the exam date.",
        ]
    )
    assert detect_language_from_text(english_page) == "English"


def test_opposite_language() -> None:
    assert opposite_language("English") == "Irish"
    assert opposite_language("Irish") == "English"
