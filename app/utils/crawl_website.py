"""Website crawling utilities built on crawl4ai.

Deep-crawls HTML pages of a site and additionally extracts the content of any
PDF documents discovered during the crawl. The starting URL defaults to the
``WEBSITE_URL`` value exposed through the application settings.

Note: this module's filename contains hyphens and a dot, so it cannot be
imported with a regular ``import`` statement. Load it via ``importlib`` if you
need to use these helpers from other modules, e.g.::

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "crawl_website_utils", "app/utils/crawl-website.utils.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    pages = module.run_crawl()
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import Coroutine
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar
from urllib.parse import urldefrag, urljoin, urlparse

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import FilterChain, URLPatternFilter
from crawl4ai.processors.pdf import PDFContentScrapingStrategy, PDFCrawlerStrategy

from app.core.config import settings

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

# File types skipped during the HTML (browser) crawl phase. PDFs are still
# discovered via page links and handled separately by ``crawl_pdfs``.
EXCLUDED_PATTERNS = ["*.mp3", "*.docx", "*.zip", "*.doc", "*.xls", "*.xlsx"]

_T = TypeVar("_T")


def _run_async(coro: Coroutine[object, object, _T]) -> _T:
    """Run a coroutine on a fresh event loop that supports subprocesses.

    On Windows, Playwright (used by crawl4ai) needs a ``ProactorEventLoop`` to
    spawn the browser subprocess. uvicorn's ``--reload`` mode runs on a
    ``SelectorEventLoop``, which cannot, so we always create our own loop here.
    Call this from a worker thread (e.g. via ``asyncio.to_thread``) when the
    caller is already inside another event loop.
    """
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        try:
            loop.close()
        finally:
            asyncio.set_event_loop(None)


@dataclass
class CrawledPage:
    """A single crawled resource (HTML page or PDF document)."""

    url: str
    content_type: str  # "html" or "pdf"
    markdown: str = ""
    metadata: dict = field(default_factory=dict)
    success: bool = False
    error: str | None = None


def _to_markdown(result) -> str:
    """Extract plain markdown text from a crawl4ai result object."""
    md = getattr(result, "markdown", None)
    if md is None:
        return ""
    raw = getattr(md, "raw_markdown", None)
    if raw is not None:
        return raw
    return str(md)


def _collect_pdf_links(result, base_url: str, same_domain: bool) -> set[str]:
    """Pull absolute ``.pdf`` URLs out of a crawl result's discovered links."""
    found: set[str] = set()
    links = getattr(result, "links", None) or {}
    base_host = urlparse(base_url).netloc

    groups = []
    if isinstance(links, dict):
        groups = [links.get("internal", []), links.get("external", [])]
    elif isinstance(links, list):
        groups = [links]

    for group in groups:
        for link in group or []:
            href = link.get("href") if isinstance(link, dict) else link
            if not href:
                continue
            absolute, _ = urldefrag(urljoin(result.url, href))
            if not absolute.lower().endswith(".pdf"):
                continue
            if same_domain and urlparse(absolute).netloc != base_host:
                continue
            found.add(absolute)
    return found


async def crawl_html_pages(
    start_url: str,
    max_depth: int = 2,
    max_pages: int = 50,
    include_external: bool = False,
) -> tuple[list[CrawledPage], set[str]]:
    """Deep-crawl HTML pages starting from ``start_url``.

    Returns the crawled HTML pages and the set of PDF URLs discovered while
    crawling so the caller can process them separately.
    """
    browser_config = BrowserConfig(headless=True)
    run_config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=max_depth,
            include_external=include_external,
            max_pages=max_pages,
            filter_chain=FilterChain([
                URLPatternFilter(patterns=EXCLUDED_PATTERNS, reverse=True),
            ]),
        ),
        cache_mode=CacheMode.BYPASS,
    )

    pages: list[CrawledPage] = []
    pdf_links: set[str] = set()

    async with AsyncWebCrawler(config=browser_config) as crawler:
        results = await crawler.arun(start_url, config=run_config)
        if not isinstance(results, list):
            results = [results]

        for result in results:
            success = bool(getattr(result, "success", False))
            pages.append(
                CrawledPage(
                    url=result.url,
                    content_type="html",
                    markdown=_to_markdown(result) if success else "",
                    metadata=getattr(result, "metadata", {}) or {},
                    success=success,
                    error=getattr(result, "error_message", None),
                )
            )
            if success:
                pdf_links |= _collect_pdf_links(
                    result, start_url, same_domain=not include_external
                )

    return pages, pdf_links


async def crawl_pdfs(pdf_urls: list[str]) -> list[CrawledPage]:
    """Extract text and metadata from a list of PDF URLs."""
    if not pdf_urls:
        return []

    run_config = CrawlerRunConfig(
        scraping_strategy=PDFContentScrapingStrategy(),
        cache_mode=CacheMode.BYPASS,
    )

    pages: list[CrawledPage] = []
    async with AsyncWebCrawler(crawler_strategy=PDFCrawlerStrategy()) as crawler:
        results = await crawler.arun_many(urls=pdf_urls, config=run_config)
        if not isinstance(results, list):
            results = [results]

        for result in results:
            markdown = _to_markdown(result)
            # crawl4ai's PDFCrawlerStrategy returns a 33-byte placeholder HTML
            # ("Scraper will handle the real work") that its anti-bot detector
            # misreads as a "near-empty content" block, flipping success=False
            # even though the PDF text was fully extracted. Recover the content
            # and treat the PDF as successful when text was actually parsed.
            crawler_success = bool(getattr(result, "success", False))
            success = crawler_success or bool(markdown.strip())
            error = getattr(result, "error_message", None)
            pages.append(
                CrawledPage(
                    url=result.url,
                    content_type="pdf",
                    markdown=markdown,
                    metadata=getattr(result, "metadata", {}) or {},
                    success=success,
                    error=None if success else error,
                )
            )

    return pages


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


def save_pages_json(
    pages: list[CrawledPage],
    source_url: str,
    output_dir: Path = OUTPUT_DIR,
    filename: str | None = None,
) -> Path:
    """Save crawled pages (markdown + metadata) as a JSON file in ``output_dir``.

    Returns the path of the written JSON file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc)
    if filename is None:
        slug = urlparse(source_url).netloc.replace(":", "_") or "crawl"
        filename = f"{slug}_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"

    payload = {
        "source_url": source_url,
        "crawled_at": timestamp.isoformat(),
        "total": len(pages),
        "pages": [asdict(page) for page in pages],
    }

    output_path = output_dir / filename
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return output_path


def run_crawl(
    url: str | None = None,
    max_depth: int = 2,
    max_pages: int = 50,
    include_pdf: bool = True,
    include_external: bool = False,
    save_json: bool = True,
) -> list[CrawledPage]:
    """Synchronous wrapper around :func:`crawl_website`.

    When ``save_json`` is True, the crawled results are also written to a JSON
    file under :data:`OUTPUT_DIR`.
    """
    start_url = url or settings.website_url
    pages = _run_async(
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


if __name__ == "__main__":
    crawled = run_crawl()
    for page in crawled:
        status = "ok" if page.success else f"failed: {page.error}"
        print(f"[{page.content_type}] {page.url} -> {len(page.markdown)} chars ({status})")
    print(f"\nTotal: {len(crawled)} resources crawled")
