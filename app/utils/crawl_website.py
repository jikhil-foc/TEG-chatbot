"""Backward-compatible facade for the website crawler.

The implementation now lives in the :mod:`app.utils.crawler` package, split
into one module per stage. This module re-exports the public API so existing
imports such as ``from app.utils.crawl_website import run_crawl`` keep working.
"""

from __future__ import annotations

from app.utils.crawler import (
    CHUNK_OUTPUT_FILENAME,
    OUTPUT_DIR,
    OUTPUT_FILENAME,
    Chunk,
    CrawledPage,
    chunk_crawled_data,
    chunk_pages,
    crawl_html_pages,
    crawl_pdfs,
    crawl_website,
    run_crawl,
    save_chunks_json,
    save_pages_json,
)

__all__ = [
    "Chunk",
    "CrawledPage",
    "CHUNK_OUTPUT_FILENAME",
    "OUTPUT_DIR",
    "OUTPUT_FILENAME",
    "chunk_crawled_data",
    "chunk_pages",
    "crawl_html_pages",
    "crawl_pdfs",
    "crawl_website",
    "run_crawl",
    "save_chunks_json",
    "save_pages_json",
]


if __name__ == "__main__":
    crawled = run_crawl()
    for page in crawled:
        status = "ok" if page.success else f"failed: {page.error}"
        print(f"[{page.content_type}] {page.url} -> {len(page.markdown)} chars ({status})")
    print(f"\nTotal: {len(crawled)} resources crawled")
