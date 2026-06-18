"""Data models shared across the crawler stages."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CrawledPage:
    """A single crawled resource (HTML page or PDF document)."""

    url: str
    content_type: str  # "html" or "pdf"
    markdown: str = ""
    language: str | None = None  # "Irish", "English" or None (<html lang> or text)
    metadata: dict = field(default_factory=dict)
    success: bool = False
    error: str | None = None
