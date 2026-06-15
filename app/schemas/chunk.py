"""Request/response models for the chunk endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChunkRequest(BaseModel):
    input_file: str | None = Field(
        default=None,
        description="Path to crawled-data.json; defaults to the standard output file",
    )
    save_json: bool = True


class ChunkingSummaryModel(BaseModel):
    total_pages_loaded: int
    html_pages_processed: int
    html_parent_chunks: int
    html_child_chunks: int
    pdf_pages_processed: int
    pdf_child_chunks: int
    total_child_chunks: int


class ChunkResponse(BaseModel):
    source_url: str
    output_file: str | None = None
    summary: ChunkingSummaryModel
