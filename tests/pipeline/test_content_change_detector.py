"""Tests for content change detection."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.pipelines.ingestion.content_change_detector import detect_content_changes
from app.pipelines.ingestion.page_section_extractor import extract_page_sections


def test_detect_content_changes_marks_unchanged_section() -> None:
    page_id = uuid4()
    section_id = uuid4()
    page = {
        "url": "https://example.com/about",
        "content_type": "html",
        "success": True,
        "language": "English",
        "metadata": {"title": "About"},
        "markdown": "# Fees\n\nCost is 100.",
    }
    extracted_section = extract_page_sections(page)[0]
    existing_section = MagicMock()
    existing_section.section_key = extracted_section.section_key
    existing_section.content_hash = extracted_section.content_hash
    existing_section.id = section_id

    repository = MagicMock()
    repository.upsert_page_record.return_value = MagicMock(page_id=page_id, is_new=False)
    repository.find_sections_by_page_id.return_value = [existing_section]
    repository.find_active_pages.return_value = []

    session = MagicMock()

    with patch(
        "app.pipelines.ingestion.content_change_detector.ContentRegistryRepository",
        return_value=repository,
    ):
        report = detect_content_changes([page], session)

    assert report.unchanged_section_ids == [str(section_id)]
    assert report.changed_sections == []


def test_detect_content_changes_marks_modified_section() -> None:
    page_id = uuid4()
    section_id = uuid4()
    existing_section = MagicMock()
    existing_section.section_key = "https://example.com/about|Fees"
    existing_section.content_hash = "old-hash"
    existing_section.id = section_id

    repository = MagicMock()
    repository.upsert_page_record.return_value = MagicMock(page_id=page_id, is_new=False)
    repository.find_sections_by_page_id.return_value = [existing_section]
    repository.find_chunk_ids_by_section_id.return_value = ["chunk-1"]
    repository.find_active_pages.return_value = []

    session = MagicMock()

    pages = [
        {
            "url": "https://example.com/about",
            "content_type": "html",
            "success": True,
            "language": "English",
            "metadata": {"title": "About"},
            "markdown": "# Fees\n\nCost is 200.",
        }
    ]

    with patch(
        "app.pipelines.ingestion.content_change_detector.ContentRegistryRepository",
        return_value=repository,
    ):
        report = detect_content_changes(pages, session)

    assert len(report.changed_sections) == 1
    assert report.removed_chunk_ids == ["chunk-1"]
    repository.upsert_section_record.assert_called_once()
