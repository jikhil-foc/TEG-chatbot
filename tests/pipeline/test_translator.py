"""Tests for cross-lingual query translation."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.config.embedding_settings import EmbeddingSettings
from app.qa.en_ga_query_translator import translate_query


@patch("app.qa.en_ga_query_translator.build_chat_model")
def test_translate_query_returns_model_output(mock_build_chat_model: MagicMock) -> None:
    mock_build_chat_model.return_value.invoke.return_value = SimpleNamespace(
        content="Cad iad na táillí scrúdaithe?"
    )
    settings = EmbeddingSettings(openai_api_key="test-key")

    translated = translate_query(
        "What are the exam fees?",
        "Irish",
        settings=settings,
    )

    assert translated == "Cad iad na táillí scrúdaithe?"
    mock_build_chat_model.return_value.invoke.assert_called_once()


@patch("app.qa.en_ga_query_translator.build_chat_model")
def test_translate_query_falls_back_on_failure(mock_build_chat_model: MagicMock) -> None:
    mock_build_chat_model.return_value.invoke.side_effect = RuntimeError("api down")
    settings = EmbeddingSettings(openai_api_key="test-key")
    original = "What are the exam fees?"

    translated = translate_query(original, "Irish", settings=settings)

    assert translated == original
