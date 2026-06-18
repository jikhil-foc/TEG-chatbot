"""Pydantic models for the ingestion pipeline API and orchestrator."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.embedding import IndexSummary


class IngestionConfig(BaseModel):
    """Parameters for a full crawl-to-Qdrant ingestion run."""

    url: str | None = Field(default=None, description="Start URL; defaults to WEBSITE_URL")
    max_depth: int = Field(default=2, ge=0, le=5)
    max_pages: int = Field(default=500, ge=1, le=500)
    include_pdf: bool = True
    include_external: bool = False
    recreate: bool = Field(
        default=False,
        description="Drop and recreate the Qdrant collection before indexing",
    )
    save_json: bool = True


class CrawlStepSummary(BaseModel):
    total: int
    succeeded: int
    failed: int
    output_file: str | None = None


class LanguageStepSummary(BaseModel):
    total: int
    irish: int
    english: int
    unknown: int
    updated: int


class ChunkStepSummary(BaseModel):
    total_pages_loaded: int
    html_pages_processed: int
    html_parent_chunks: int
    html_child_chunks: int
    pdf_pages_processed: int
    pdf_child_chunks: int
    total_child_chunks: int
    output_file: str | None = None


class IngestionResult(BaseModel):
    """Aggregated result of a full ingestion pipeline run."""

    source_url: str
    steps_completed: list[str]
    crawl: CrawlStepSummary
    language: LanguageStepSummary
    chunk: ChunkStepSummary
    index: IndexSummary
