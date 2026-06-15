"""Website crawler package.

Deep-crawls HTML pages of a site and additionally extracts the content of any
PDF documents discovered during the crawl. The starting URL defaults to the
``WEBSITE_URL`` value exposed through the application settings.

The crawl is split into stages, one module each:

* :mod:`app.pipeline.crawl.config` -- shared constants/configuration.
* :mod:`app.pipeline.crawl.models` -- the :class:`CrawledPage` data model.
* :mod:`app.pipeline.crawl.text` -- markdown cleanup and language detection.
* :mod:`app.pipeline.crawl.html_stage` -- HTML deep crawl + PDF link discovery.
* :mod:`app.pipeline.crawl.pdf_stage` -- PDF fetch and text extraction.
* :mod:`app.pipeline.crawl.storage` -- JSON persistence.
* :mod:`app.pipeline.crawl.runner` -- orchestration and entry points.
"""

from __future__ import annotations

from app.pipeline.crawl.config import OUTPUT_DIR, OUTPUT_FILENAME
from app.pipeline.crawl.html_stage import crawl_html_pages
from app.pipeline.crawl.models import CrawledPage
from app.pipeline.crawl.pdf_stage import crawl_pdfs
from app.pipeline.crawl.runner import crawl_website, run_crawl
from app.pipeline.crawl.storage import save_pages_json

__all__ = [
    "CrawledPage",
    "OUTPUT_DIR",
    "OUTPUT_FILENAME",
    "crawl_html_pages",
    "crawl_pdfs",
    "crawl_website",
    "run_crawl",
    "save_pages_json",
]
