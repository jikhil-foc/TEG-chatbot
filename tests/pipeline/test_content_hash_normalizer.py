"""Tests for content hash normalization."""

from __future__ import annotations

from app.pipelines.ingestion.content_hash_normalizer import (
    compute_content_hash,
    normalize_content_for_hash,
    sanitize_text_for_storage,
)


def test_normalize_content_for_hash_collapses_whitespace() -> None:
    assert normalize_content_for_hash("hello\n\n  world") == "hello world"


def test_compute_content_hash_is_stable() -> None:
    first = compute_content_hash("same   text")
    second = compute_content_hash("same text")
    assert first == second


def test_compute_content_hash_detects_changes() -> None:
    assert compute_content_hash("alpha") != compute_content_hash("beta")


def test_sanitize_text_for_storage_removes_nul_bytes() -> None:
    assert sanitize_text_for_storage("hello\x00world") == "helloworld"
