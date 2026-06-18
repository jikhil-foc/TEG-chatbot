"""Tests for cross-lingual answer generation instructions."""

from __future__ import annotations

from app.services.grounded_answer import _language_instruction


def test_language_instruction_same_language() -> None:
    assert _language_instruction("English") == " Respond in English."
    assert _language_instruction("Irish") == " Respond in Irish."


def test_language_instruction_cross_lingual_context() -> None:
    instruction = _language_instruction("English", context_language="Irish")

    assert "Respond in English." in instruction
    assert "context is in Irish" in instruction
    assert "in English in your answer" in instruction
