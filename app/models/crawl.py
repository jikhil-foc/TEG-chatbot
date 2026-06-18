"""Request/response models for the crawl endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CrawlRequest(BaseModel):
    url: str | None = Field(default=None, description="Start URL; defaults to WEBSITE_URL")
    max_depth: int = Field(default=2, ge=0, le=5)
    max_pages: int = Field(default=500, ge=1, le=500)
    include_pdf: bool = True
    include_external: bool = False
    save_json: bool = True


class CrawlResponse(BaseModel):
    source_url: str
    total: int
    succeeded: int
    failed: int
    output_file: str | None = None
