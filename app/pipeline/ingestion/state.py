"""Typed state for the LangGraph ingestion workflow."""

from __future__ import annotations

from typing import TypedDict


class IngestionState(TypedDict, total=False):
    """Mutable state passed between ingestion graph nodes."""

    # Request parameters
    url: str
    max_depth: int
    max_pages: int
    include_pdf: bool
    include_external: bool
    recreate: bool
    save_json: bool

    # Crawl outputs
    source_url: str
    crawled_file: str
    crawl_total: int
    crawl_succeeded: int
    crawl_failed: int

    # Language detection outputs
    language_total: int
    language_irish: int
    language_english: int
    language_unknown: int
    language_updated: int

    # Chunk outputs
    chunked_file: str
    chunk_total_pages_loaded: int
    chunk_html_pages_processed: int
    chunk_html_parent_chunks: int
    chunk_html_child_chunks: int
    chunk_pdf_pages_processed: int
    chunk_pdf_child_chunks: int
    chunk_total_child_chunks: int

    # Index outputs
    index_collection_name: str
    index_total_documents: int
    index_uploaded: int
    index_batches: int
    index_recreated_collection: bool

    # Progress tracking
    steps_completed: list[str]
