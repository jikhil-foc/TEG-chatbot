"""Orchestration stage: combine HTML/PDF crawl stages and expose entry points."""

from __future__ import annotations

from app.core.config import settings
from app.utils.crawler.html_stage import crawl_html_pages
from app.utils.crawler.models import CrawledPage
from app.utils.crawler.pdf_stage import crawl_pdfs
from app.utils.crawler.runtime import run_async
from app.utils.crawler.storage import save_pages_json


async def crawl_website(
    url: str | None = None,
    max_depth: int = 2,
    max_pages: int = 50,
    include_pdf: bool = True,
    include_external: bool = False,
) -> list[CrawledPage]:
    """Crawl a website (HTML pages plus discovered PDFs).

    Args:
        url: Starting URL. Defaults to ``settings.website_url``.
        max_depth: Levels to crawl beyond the starting page.
        max_pages: Maximum number of HTML pages to crawl.
        include_pdf: Whether to also extract discovered PDF documents.
        include_external: Whether to follow links to other domains.

    Returns:
        Combined list of crawled HTML pages and PDF documents.
    """
    start_url = url or settings.website_url

    pages, pdf_links = await crawl_html_pages(
        start_url,
        max_depth=max_depth,
        max_pages=max_pages,
        include_external=include_external,
    )

    if include_pdf and pdf_links:
        pages.extend(await crawl_pdfs(sorted(pdf_links)))

    return pages


def run_crawl(
    url: str | None = None,
    max_depth: int = 2,
    max_pages: int = 50,
    include_pdf: bool = True,
    include_external: bool = False,
    save_json: bool = True,
) -> list[CrawledPage]:
    """Synchronous wrapper around :func:`crawl_website`.

    When ``save_json`` is True, the crawled results are written to a JSON file
    under :data:`app.utils.crawler.config.OUTPUT_DIR`.
    """
    start_url = url or settings.website_url
    pages = run_async(
        crawl_website(
            url=start_url,
            max_depth=max_depth,
            max_pages=max_pages,
            include_pdf=include_pdf,
            include_external=include_external,
        )
    )

    if save_json:
        output_path = save_pages_json(pages, source_url=start_url)
        print(f"Saved {len(pages)} pages to {output_path}")

    return pages
