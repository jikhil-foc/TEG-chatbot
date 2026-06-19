"""PostgreSQL content registry persistence layer."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, joinedload

from app.db.orm_models import ChunkRecord, PageRecord, SectionRecord
from app.pipelines.ingestion.content_hash_normalizer import sanitize_text_for_storage
from app.pipelines.ingestion.langchain_page_chunker import ChildChunk, dedupe_chunks_by_id
from app.pipelines.ingestion.page_section_extractor import build_section_id, build_section_key


@dataclass
class PageUpsertResult:
    """Result of upserting a crawled page record."""

    page_id: uuid.UUID
    is_new: bool


class ContentRegistryRepository:
    """CRUD and query operations for the content registry tables."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_page_record(
        self,
        *,
        url: str,
        title: str | None,
        content_type: str,
        language: str | None,
    ) -> PageUpsertResult:
        """Insert or update a page row keyed by URL."""
        record = self._session.scalar(select(PageRecord).where(PageRecord.url == url))
        now = datetime.now(UTC)
        if record is None:
            record = PageRecord(
                url=url,
                title=title,
                content_type=content_type,
                language=language,
                last_crawled_at=now,
                is_active=True,
            )
            self._session.add(record)
            self._session.flush()
            return PageUpsertResult(page_id=record.id, is_new=True)

        record.title = title
        record.content_type = content_type
        record.language = language
        record.last_crawled_at = now
        record.is_active = True
        self._session.flush()
        return PageUpsertResult(page_id=record.id, is_new=False)

    def find_page_by_url(self, url: str) -> PageRecord | None:
        return self._session.scalar(select(PageRecord).where(PageRecord.url == url))

    def find_active_pages(self) -> list[PageRecord]:
        return list(
            self._session.scalars(
                select(PageRecord).where(PageRecord.is_active.is_(True))
            ).all()
        )

    def find_sections_by_page_id(self, page_id: uuid.UUID) -> list[SectionRecord]:
        return list(
            self._session.scalars(
                select(SectionRecord).where(SectionRecord.page_id == page_id)
            ).all()
        )

    def find_section_by_page_and_key(
        self,
        page_id: uuid.UUID,
        section_key: str,
    ) -> SectionRecord | None:
        return self._session.scalar(
            select(SectionRecord).where(
                SectionRecord.page_id == page_id,
                SectionRecord.section_key == section_key,
            )
        )

    def upsert_section_record(self, page_id: uuid.UUID, section: PageSection) -> SectionRecord:
        """Insert or update a section row for the given page."""
        record = self.find_section_by_page_and_key(page_id, section.section_key)
        section_uuid = uuid.UUID(section.section_id)
        if record is None:
            record = SectionRecord(
                id=section_uuid,
                page_id=page_id,
                section_key=section.section_key,
                header_path=section.header_path,
                content_hash=section.content_hash,
                content=section.content,
            )
            self._session.add(record)
        else:
            record.header_path = section.header_path
            record.content_hash = section.content_hash
            record.content = section.content
            record.updated_at = datetime.now(UTC)
        self._session.flush()
        return record

    def find_chunk_ids_by_section_id(self, section_id: uuid.UUID) -> list[str]:
        rows = self._session.scalars(
            select(ChunkRecord.chunk_id).where(ChunkRecord.section_id == section_id)
        ).all()
        return list(rows)

    def find_all_chunk_records(self) -> list[ChunkRecord]:
        statement = select(ChunkRecord).options(
            joinedload(ChunkRecord.section).joinedload(SectionRecord.page)
        )
        return list(self._session.scalars(statement).unique().all())

    def load_child_chunks_from_registry(self) -> list[ChildChunk]:
        """Rebuild :class:`ChildChunk` objects from persisted registry rows."""
        chunks: list[ChildChunk] = []
        for record in self.find_all_chunk_records():
            section = record.section
            page = section.page
            chunks.append(
                ChildChunk(
                    chunk_id=record.chunk_id,
                    parent_chunk_id=record.parent_chunk_id,
                    url=page.url,
                    title=page.title or "",
                    language=page.language,
                    content_type=page.content_type,
                    header_path=list(section.header_path or []),
                    chunk_level="child",
                    chunk_index=record.chunk_index,
                    content=record.content,
                    section_id=str(section.id),
                    content_hash=record.content_hash,
                    section_content_hash=section.content_hash,
                )
            )
        return chunks

    def clear_content_registry(self) -> None:
        """Remove all rows from the content registry tables."""
        self._session.execute(delete(ChunkRecord))
        self._session.execute(delete(SectionRecord))
        self._session.execute(delete(PageRecord))
        self._session.flush()

    def replace_section_chunks(
        self,
        section_id: uuid.UUID,
        chunks: list[ChildChunk],
    ) -> None:
        """Delete existing chunk rows for a section and insert the new set."""
        chunks = dedupe_chunks_by_id(chunks)
        existing = self._session.scalars(
            select(ChunkRecord).where(ChunkRecord.section_id == section_id)
        ).all()
        for row in existing:
            self._session.delete(row)
        self._session.flush()

        for chunk in chunks:
            self._session.add(
                ChunkRecord(
                    section_id=section_id,
                    chunk_id=chunk.chunk_id,
                    parent_chunk_id=chunk.parent_chunk_id,
                    chunk_index=chunk.chunk_index,
                    content_hash=chunk.content_hash,
                    content=sanitize_text_for_storage(chunk.content),
                    vector_id=chunk.chunk_id,
                )
            )
        self._session.flush()

    def mark_page_inactive(self, url: str) -> PageRecord | None:
        record = self.find_page_by_url(url)
        if record is None:
            return None
        record.is_active = False
        self._session.flush()
        return record

    def delete_section_cascade(self, section_id: uuid.UUID) -> list[str]:
        """Delete a section and its chunk rows; return removed chunk IDs."""
        record = self._session.get(SectionRecord, section_id)
        if record is None:
            return []
        chunk_ids = [chunk.chunk_id for chunk in record.chunks]
        self._session.delete(record)
        self._session.flush()
        return chunk_ids

    def populate_registry_from_chunks(
        self,
        pages: list[dict],
        chunks: list[ChildChunk],
        *,
        replace_existing: bool = True,
    ) -> None:
        """Populate the full registry after a baseline ingest."""
        if replace_existing:
            self.clear_content_registry()

        chunks = dedupe_chunks_by_id(chunks)
        page_id_by_url: dict[str, uuid.UUID] = {}
        for page in pages:
            if not page.get("success"):
                continue
            url = page.get("url", "")
            if not url:
                continue
            metadata = page.get("metadata", {})
            result = self.upsert_page_record(
                url=url,
                title=metadata.get("title", ""),
                content_type=page.get("content_type", "html"),
                language=page.get("language"),
            )
            page_id_by_url[url] = result.page_id

        section_id_by_key: dict[str, uuid.UUID] = {}
        for chunk in chunks:
            section_key = build_section_key(chunk.url, chunk.header_path)
            if section_key not in section_id_by_key:
                page_id = page_id_by_url.get(chunk.url)
                if page_id is None:
                    continue
                section_uuid = uuid.UUID(chunk.section_id) if chunk.section_id else uuid.UUID(
                    build_section_id(section_key)
                )
                record = self.find_section_by_page_and_key(page_id, section_key)
                if record is None:
                    record = SectionRecord(
                        id=section_uuid,
                        page_id=page_id,
                        section_key=section_key,
                        header_path=chunk.header_path,
                        content_hash=chunk.section_content_hash or chunk.content_hash,
                        content=None,
                    )
                    self._session.add(record)
                    self._session.flush()
                section_id_by_key[section_key] = record.id

        chunks_by_section: dict[uuid.UUID, list[ChildChunk]] = {}
        for chunk in chunks:
            section_key = build_section_key(chunk.url, chunk.header_path)
            section_id = section_id_by_key.get(section_key)
            if section_id is None:
                continue
            bucket = chunks_by_section.setdefault(section_id, [])
            if any(existing.chunk_id == chunk.chunk_id for existing in bucket):
                continue
            bucket.append(chunk)

        for section_id, section_chunks in chunks_by_section.items():
            self.replace_section_chunks(section_id, section_chunks)


def get_content_registry_counts(session: Session) -> dict[str, int]:
    """Return row counts for pages, sections, and chunks."""
    return {
        "pages": session.scalar(select(func.count()).select_from(PageRecord)) or 0,
        "sections": session.scalar(select(func.count()).select_from(SectionRecord)) or 0,
        "chunks": session.scalar(select(func.count()).select_from(ChunkRecord)) or 0,
    }
