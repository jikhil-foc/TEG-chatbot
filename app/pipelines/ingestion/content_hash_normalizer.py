"""Content hashing helpers for incremental ingestion."""

from __future__ import annotations

import hashlib


def sanitize_text_for_storage(content: str) -> str:
    """Remove NUL bytes that PostgreSQL ``TEXT`` columns cannot store."""
    if not content:
        return ""
    return content.replace("\x00", "")


def normalize_content_for_hash(content: str) -> str:
    """Collapse whitespace so cosmetic formatting changes do not invalidate hashes."""
    return " ".join(sanitize_text_for_storage(content).split())


def compute_content_hash(content: str) -> str:
    """Return a SHA-256 hex digest of normalized ``content``."""
    normalized = normalize_content_for_hash(content)
    return hashlib.sha256(normalized.encode()).hexdigest()
