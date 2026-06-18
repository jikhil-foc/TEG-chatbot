"""Extract header-delimited sections from crawled page records."""

from __future__ import annotations

import uuid

from langchain_text_splitters import MarkdownHeaderTextSplitter

from app.pipelines.ingestion.content_hash_normalizer import (
    compute_content_hash,
    sanitize_text_for_storage,
)
from app.pipelines.ingestion.page_section import PageSection

_MARKDOWN_HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]
_SECTION_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

_header_splitter: MarkdownHeaderTextSplitter | None = None


def _get_header_splitter() -> MarkdownHeaderTextSplitter:
    global _header_splitter
    if _header_splitter is None:
        _header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=_MARKDOWN_HEADERS,
            strip_headers=False,
        )
    return _header_splitter


def _header_path(metadata: dict) -> list[str]:
    return [metadata[key] for _, key in _MARKDOWN_HEADERS if metadata.get(key)]


def build_section_key(url: str, header_path: list[str]) -> str:
    """Build a stable section identifier from URL and heading hierarchy."""
    path = "/".join(header_path) if header_path else "__root__"
    return f"{url}|{path}"


def build_section_id(section_key: str) -> str:
    """Derive a deterministic UUID string from ``section_key``."""
    return str(uuid.uuid5(_SECTION_NAMESPACE, section_key))


def extract_page_sections(page: dict) -> list[PageSection]:
    """Extract sections from one crawled page dict (HTML or PDF)."""
    if not page.get("success"):
        return []

    markdown = sanitize_text_for_storage((page.get("markdown") or "").strip())
    if not markdown:
        return []

    url = page.get("url", "")
    page_metadata = page.get("metadata", {})
    title = page_metadata.get("title", "")
    language = page.get("language")
    content_type = page.get("content_type", "html")

    if content_type == "pdf":
        section_key = build_section_key(url, [])
        return [
            PageSection(
                url=url,
                title=title,
                language=language,
                content_type=content_type,
                header_path=[],
                section_key=section_key,
                section_id=build_section_id(section_key),
                content=markdown,
                content_hash=compute_content_hash(markdown),
            )
        ]

    if content_type != "html":
        return []

    header_splitter = _get_header_splitter()
    sections: list[PageSection] = []
    for section in header_splitter.split_text(markdown):
        header_path = _header_path(section.metadata)
        content = (section.page_content or "").strip()
        if not content:
            continue
        section_key = build_section_key(url, header_path)
        sections.append(
            PageSection(
                url=url,
                title=title,
                language=language,
                content_type=content_type,
                header_path=header_path,
                section_key=section_key,
                section_id=build_section_id(section_key),
                content=content,
                content_hash=compute_content_hash(content),
            )
        )
    return sections
