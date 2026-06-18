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
    section_id: str = ""
    content_hash: str = ""


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
    dense_embeddings_generated: int = 0


class IndexRequest(BaseModel):
    input_file: str | None = Field(
        default=None,
        description="Path to chunked_data.json; defaults to the configured input path",
    )
    recreate: bool = Field(
        default=False,
        description="Drop and recreate the Qdrant collection before indexing",
    )


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    top_k: int = Field(default=10, ge=1, le=100)
    expand_to_parent: bool = Field(
        default=True,
        description="Expand each match to its full parent section before returning",
    )


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
