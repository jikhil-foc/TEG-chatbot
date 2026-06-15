"""Request models for the ingestion pipeline endpoint.

The response model (:class:`IngestionResult`) and config object
(:class:`IngestionConfig`) are domain models that live in
:mod:`app.pipeline.ingestion.models`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
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
