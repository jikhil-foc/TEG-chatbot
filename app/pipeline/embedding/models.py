"""Pydantic models shared across the embedding pipeline."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    """The metadata payload stored alongside each chunk in Qdrant."""

    chunk_id: str
    parent_chunk_id: str
    url: str
    title: str
    content_type: str
    header_path: list[str] = Field(default_factory=list)
    chunk_index: int = 0
    raw_content: str = ""
    token_count: int


class SearchResult(BaseModel):
    """A single hybrid-search hit returned to callers."""

    chunk_id: str
    score: float
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class IndexSummary(BaseModel):
    """Aggregate counts describing an indexing run."""

    collection_name: str
    total_documents: int
    uploaded: int
    batches: int
    recreated_collection: bool
