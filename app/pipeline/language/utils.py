"""Shared language helpers for the QA and ingestion pipelines."""

from __future__ import annotations

_SUPPORTED_LANGUAGES = frozenset({"English", "Irish"})


def opposite_language(language: str) -> str:
    """Return the other supported UI language (English ↔ Irish)."""
    if language == "Irish":
        return "English"
    if language == "English":
        return "Irish"
    raise ValueError(
        f"Unsupported language {language!r}; expected one of {sorted(_SUPPORTED_LANGUAGES)}"
    )
