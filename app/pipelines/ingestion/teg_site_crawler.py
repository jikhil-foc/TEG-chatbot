"""Public entry point for the TEG website crawl pipeline.

Re-exports crawl orchestration, persistence helpers and the :class:`CrawledPage`
model so API routes and LangGraph nodes can depend on a single import path.
"""

from app.pipelines.ingestion.crawl_runner import crawl_website, run_crawl
from app.pipelines.ingestion.crawl_json_writer import save_pages_json
from app.pipelines.ingestion.crawled_page import CrawledPage
from app.pipelines.ingestion.html_page_extractor import crawl_html_pages
from app.pipelines.ingestion.pdf_document_extractor import crawl_pdfs
from app.config.data_paths import DATA_DIR, CRAWLED_DATA_FILENAME

OUTPUT_DIR = DATA_DIR
OUTPUT_FILENAME = CRAWLED_DATA_FILENAME

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
