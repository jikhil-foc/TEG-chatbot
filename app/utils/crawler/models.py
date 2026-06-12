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


@dataclass
class Chunk:
    """A single text chunk derived from a crawled page's markdown."""

    chunk_id: str  # unique id (UUID4)
    source_url: str
    content_type: str  # "html" or "pdf"
    language: str | None  # inherited from the source page
    chunk_index: int  # position of this chunk within its source page
    text: str
    char_count: int
    section: str | None = None  # heading breadcrumb, e.g. "TEG Levels > Fees"
    metadata: dict = field(default_factory=dict)  # carries page title etc.
