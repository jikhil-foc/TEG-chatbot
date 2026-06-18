"""Populate content registry after a baseline ingest."""

from __future__ import annotations

import json
from pathlib import Path

from app.db.content_registry_repository import ContentRegistryRepository
from app.db.database_session import session_scope
from app.pipelines.ingestion.content_hash_normalizer import (
    compute_content_hash,
    sanitize_text_for_storage,
)
from app.pipelines.ingestion.langchain_page_chunker import ChildChunk, load
from app.pipelines.ingestion.page_section_extractor import build_section_id, build_section_key


def _child_chunk_from_record(record: dict) -> ChildChunk:
    content = sanitize_text_for_storage(record.get("content", ""))
    header_path = record.get("header_path", []) or []
    url = record.get("url", "")
    section_key = build_section_key(url, header_path)
    return ChildChunk(
        chunk_id=record["chunk_id"],
        parent_chunk_id=record.get("parent_chunk_id", record["chunk_id"]),
        url=url,
        title=record.get("title", ""),
        language=record.get("language"),
        content_type=record.get("content_type", "html"),
        header_path=header_path,
        chunk_level=record.get("chunk_level", "child"),
        chunk_index=record.get("chunk_index", 0),
        content=content,
        section_id=record.get("section_id") or build_section_id(section_key),
        content_hash=record.get("content_hash") or compute_content_hash(content),
        section_content_hash=record.get("section_content_hash", ""),
    )


def populate_content_registry_from_baseline(
    crawled_file: Path,
    chunked_file: Path,
) -> None:
    """Seed PostgreSQL registry tables from baseline crawl/chunk JSON artifacts."""
    crawled_pages = load(crawled_file)
    chunked_payload = json.loads(chunked_file.read_text(encoding="utf-8"))
    chunks = [_child_chunk_from_record(record) for record in chunked_payload]

    with session_scope() as session:
        repository = ContentRegistryRepository(session)
        repository.populate_registry_from_chunks(crawled_pages, chunks)
