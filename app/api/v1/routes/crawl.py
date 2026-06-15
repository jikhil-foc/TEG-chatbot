import asyncio

from fastapi import APIRouter

from app.core.config import settings
from app.pipeline.crawl import run_crawl, save_pages_json
from app.schemas.crawl import CrawlRequest, CrawlResponse

router = APIRouter()


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
