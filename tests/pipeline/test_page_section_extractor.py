"""Tests for page section extraction."""

from __future__ import annotations

from app.pipelines.ingestion.page_section_extractor import (
    build_section_id,
    build_section_key,
    extract_page_sections,
)


def test_build_section_key_uses_root_for_empty_header_path() -> None:
    assert build_section_key("https://example.com", []) == "https://example.com|__root__"


def test_build_section_id_is_deterministic() -> None:
    section_key = build_section_key("https://example.com", ["Fees"])
    assert build_section_id(section_key) == build_section_id(section_key)


def test_extract_page_sections_from_html_markdown() -> None:
    page = {
        "url": "https://example.com/about",
        "content_type": "html",
        "success": True,
        "language": "English",
        "metadata": {"title": "About"},
        "markdown": "# Fees\n\nCost is 100.\n\n## Details\n\nMore info.",
    }

    sections = extract_page_sections(page)

    assert len(sections) == 2
    assert sections[0].header_path == ["Fees"]
    assert "Cost is 100." in sections[0].content
    assert sections[1].header_path == ["Fees", "Details"]


def test_extract_page_sections_from_pdf_page() -> None:
    page = {
        "url": "https://example.com/doc.pdf",
        "content_type": "pdf",
        "success": True,
        "language": "English",
        "metadata": {"title": "Document"},
        "markdown": "PDF body text",
    }

    sections = extract_page_sections(page)

    assert len(sections) == 1
    assert sections[0].header_path == []
    assert sections[0].content == "PDF body text"
