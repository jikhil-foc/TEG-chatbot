import asyncio

from pydantic import BaseModel, Field
from fastapi import APIRouter

from app.core.config import settings
from app.pipeline.crawl_website import run_crawl, save_pages_json

router = APIRouter()


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


@router.post("", response_model=CrawlResponse)
async def crawl(request: CrawlRequest) -> CrawlResponse:
    start_url = request.url or settings.website_url

    pages = await asyncio.to_thread(
        run_crawl,
        url=start_url,
        max_depth=request.max_depth,
        max_pages=request.max_pages,
        include_pdf=request.include_pdf,
        include_external=request.include_external,
        save_json=False,
    )

    output_file: str | None = None
    if request.save_json:
        output_file = str(save_pages_json(pages, source_url=start_url))

    succeeded = sum(1 for page in pages if page.success)
    return CrawlResponse(
        source_url=start_url,
        total=len(pages),
        succeeded=succeeded,
        failed=len(pages) - succeeded,
        output_file=output_file,
    )
