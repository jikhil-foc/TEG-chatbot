"""Tests for LangSmith configuration helpers."""

from __future__ import annotations

import os

import pytest

from app.utils import langsmith_tracing as langsmith_module


@pytest.fixture(autouse=True)
def _reset_langsmith_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate LangSmith env side effects between tests."""
    langsmith_module._CONFIGURED = False
    langsmith_module.get_langsmith_settings.cache_clear()
    for key in (
        "LANGSMITH_TRACING",
        "LANGSMITH_API_KEY",
        "LANGSMITH_PROJECT",
        "LANGSMITH_ENDPOINT",
        "LANGCHAIN_TRACING_V2",
        "LANGCHAIN_API_KEY",
        "LANGCHAIN_PROJECT",
    ):
        monkeypatch.delenv(key, raising=False)


def test_configure_langsmith_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.setattr(
        langsmith_module,
        "get_langsmith_settings",
        lambda: langsmith_module.LangSmithSettings(langsmith_tracing=False),
    )

    assert langsmith_module.configure_langsmith() is False
    assert os.environ.get("LANGSMITH_TRACING") is None


def test_configure_langsmith_sets_env_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2_test_key")
    monkeypatch.setenv("LANGSMITH_PROJECT", "test-project")
    langsmith_module.get_langsmith_settings.cache_clear()

    assert langsmith_module.configure_langsmith() is True
    assert os.environ["LANGSMITH_TRACING"] == "true"
    assert os.environ["LANGSMITH_API_KEY"] == "lsv2_test_key"
    assert os.environ["LANGSMITH_PROJECT"] == "test-project"
    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"


def test_build_run_config_includes_metadata() -> None:
    config = langsmith_module.build_run_config(
        run_name="qa_pipeline",
        tags=["qa"],
        metadata={"query": "hello"},
    )

    assert config == {
        "run_name": "qa_pipeline",
        "tags": ["qa"],
        "metadata": {"query": "hello"},
    }
