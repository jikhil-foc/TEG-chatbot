"""Detect section-level content changes between a crawl and PostgreSQL."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.content_registry_repository import ContentRegistryRepository
from app.pipelines.ingestion.content_change_report import ContentChangeReport
from app.pipelines.ingestion.page_section_extractor import extract_page_sections


def detect_content_changes(
    crawled_pages: list[dict],
    session: Session,
) -> ContentChangeReport:
    """Compare freshly crawled pages against the content registry."""
    repository = ContentRegistryRepository(session)
    report = ContentChangeReport()
    crawled_urls: set[str] = set()

    for page in crawled_pages:
        if not page.get("success"):
            continue
        url = page.get("url", "")
        if not url:
            continue
        crawled_urls.add(url)

        page_metadata = page.get("metadata", {})
        page_result = repository.upsert_page_record(
            url=url,
            title=page_metadata.get("title", ""),
            content_type=page.get("content_type", "html"),
            language=page.get("language"),
        )
        existing_sections = {
            section.section_key: section
            for section in repository.find_sections_by_page_id(page_result.page_id)
        }
        seen_section_keys: set[str] = set()

        for section in extract_page_sections(page):
            seen_section_keys.add(section.section_key)
            existing = existing_sections.get(section.section_key)
            if existing is None or existing.content_hash != section.content_hash:
                if existing is not None:
                    report.removed_chunk_ids.extend(
                        repository.find_chunk_ids_by_section_id(existing.id)
                    )
                repository.upsert_section_record(page_result.page_id, section)
                report.changed_sections.append(section)
            else:
                report.unchanged_section_ids.append(str(existing.id))

        for section_key, existing in existing_sections.items():
            if section_key not in seen_section_keys:
                section_id = existing.id
                chunk_ids = repository.find_chunk_ids_by_section_id(section_id)
                report.removed_section_ids.append(str(section_id))
                report.removed_chunk_ids.extend(chunk_ids)
                repository.delete_section_cascade(section_id)

    for page in repository.find_active_pages():
        if page.url not in crawled_urls:
            for section in repository.find_sections_by_page_id(page.id):
                chunk_ids = repository.find_chunk_ids_by_section_id(section.id)
                report.removed_section_ids.append(str(section.id))
                report.removed_chunk_ids.extend(chunk_ids)
                repository.delete_section_cascade(section.id)
            repository.mark_page_inactive(page.url)

    return report
