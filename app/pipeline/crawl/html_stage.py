"""HTML crawl stage: deep-crawl pages and discover PDF links."""

from __future__ import annotations

from urllib.parse import urldefrag, urljoin, urlparse

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import FilterChain, URLPatternFilter

from app.pipeline.crawl.config import (
    EXCLUDED_PATTERNS,
    EXCLUDED_SELECTOR,
    EXCLUDED_TAGS,
)
from app.pipeline.crawl.models import CrawledPage
from app.pipeline.crawl.text import detect_language, to_markdown


def collect_pdf_links(result, base_url: str, same_domain: bool) -> set[str]:
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
        # Strip non-content chrome so the extracted markdown stays focused on
        # the page's main text instead of images, header/footer/nav and widgets.
        excluded_tags=EXCLUDED_TAGS,
        excluded_selector=EXCLUDED_SELECTOR,
        exclude_all_images=True,
        remove_overlay_elements=True,
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
                    markdown=to_markdown(result) if success else "",
                    language=detect_language(result) if success else None,
                    metadata=getattr(result, "metadata", {}) or {},
                    success=success,
                    error=getattr(result, "error_message", None),
                )
            )
            if success:
                pdf_links |= collect_pdf_links(
                    result, start_url, same_domain=not include_external
                )

    return pages, pdf_links
