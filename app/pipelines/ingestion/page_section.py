"""A header-delimited section extracted from a crawled page."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PageSection:
    """A single section ready for hashing, chunking, or change detection."""

    url: str
    title: str
    language: str | None
    content_type: str
    header_path: list[str]
    section_key: str
    section_id: str
    content: str
    content_hash: str
