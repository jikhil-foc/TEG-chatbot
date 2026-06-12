"""Website crawler package.

Deep-crawls HTML pages of a site and additionally extracts the content of any
PDF documents discovered during the crawl. The starting URL defaults to the
``WEBSITE_URL`` value exposed through the application settings.

The crawl is split into stages, one module each:

* :mod:`app.utils.crawler.config` -- shared constants/configuration.
* :mod:`app.utils.crawler.models` -- the :class:`CrawledPage` data model.
* :mod:`app.utils.crawler.text` -- markdown cleanup and language detection.
* :mod:`app.utils.crawler.html_stage` -- HTML deep crawl + PDF link discovery.
* :mod:`app.utils.crawler.pdf_stage` -- PDF fetch and text extraction.
* :mod:`app.utils.crawler.storage` -- JSON persistence.
* :mod:`app.utils.crawler.runner` -- orchestration and entry points.
"""

from __future__ import annotations

from app.utils.crawler.chunk_stage import chunk_crawled_data, chunk_pages
from app.utils.crawler.config import (
    CHUNK_OUTPUT_FILENAME,
    OUTPUT_DIR,
    OUTPUT_FILENAME,
)
from app.utils.crawler.html_stage import crawl_html_pages
from app.utils.crawler.models import Chunk, CrawledPage
from app.utils.crawler.pdf_stage import crawl_pdfs
from app.utils.crawler.runner import crawl_website, run_crawl
from app.utils.crawler.storage import save_chunks_json, save_pages_json

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
