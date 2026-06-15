"""Request/response models for the embedding endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.pipeline.embedding.models import SearchResult


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
