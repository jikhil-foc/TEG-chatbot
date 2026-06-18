"""Request models for the ingestion pipeline endpoint.

The response model (:class:`IngestionResult`) and config object
(:class:`IngestionConfig`) are domain models in
:mod:`app.models.ingest_request`.
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
    incremental: bool = Field(
        default=False,
        description="Detect section-level changes and update only affected chunks",
    )
    baseline: bool = Field(
        default=False,
        description="Run full chunk/index path and populate the PostgreSQL registry",
    )
