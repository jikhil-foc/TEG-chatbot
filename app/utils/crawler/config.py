"""Shared configuration and constants for the website crawler stages."""

from __future__ import annotations

from pathlib import Path

import httpx

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "output"
OUTPUT_FILENAME = "crawled-data.json"

# --- Chunking stage ----------------------------------------------------------
# Output file for the hybrid (semantic + recursive) chunking stage.
CHUNK_OUTPUT_FILENAME = "crawled-chunked-data.json"

# Multilingual sentence-transformers model used for semantic chunking. Handles
# both Irish and English content found on teg.ie. Downloaded once from Hugging
# Face and cached locally for subsequent (offline) runs.
EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Recursive size cap applied to each semantic chunk (character counts).
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

# Chunks shorter than this (characters) are merged into an adjacent chunk so
# the output contains no tiny, context-poor fragments (e.g. lone headings).
CHUNK_MIN_SIZE = 250

# Upper bound for a merged chunk. Slightly above CHUNK_SIZE so a small fragment
# (or a heading) can be folded into a full-sized neighbour without splitting.
CHUNK_MERGE_CEILING = int(CHUNK_SIZE * 1.25)

# Markdown header levels used to split each page into sections before semantic
# chunking, so headings stay attached to the text beneath them and provide a
# breadcrumb for each chunk. Ordered from most to least significant.
MARKDOWN_HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]

# Semantic breakpoint percentile. Within an oversized section, a split is made
# wherever the embedding cosine-distance between consecutive sentences exceeds
# this percentile of all such distances (higher = fewer, larger segments).
SEMANTIC_BREAKPOINT_PERCENTILE = 95.0

# File types skipped during the HTML (browser) crawl phase. PDFs are still
# discovered via page links and handled separately by the PDF stage.
EXCLUDED_PATTERNS = ["*.mp3", "*.docx", "*.zip", "*.doc", "*.xls", "*.xlsx", "*.pdf","*.wmv","*.mp4"]

# PDFs are fetched over HTTP into memory (no temp files on disk).
PDF_FETCH_TIMEOUT = httpx.Timeout(connect=20.0, read=600.0, write=20.0, pool=20.0)
PDF_MAX_CONCURRENT = 10

# Whole HTML tags stripped before markdown generation so chrome like the
# site header, footer and navigation never reaches the extracted content.
EXCLUDED_TAGS = ["header", "footer", "nav", "aside"]

# CSS selectors for non-content widgets (carousels/sliders, icon-only
# elements, decorative SVGs, leftover nav/menu blocks and cookie/consent
# banners). Combined into the single comma-separated string crawl4ai's
# ``excluded_selector`` expects.
EXCLUDED_SELECTOR = ", ".join([
    ".carousel", ".slider", ".swiper", ".slick", "[class*='carousel']",
    "[class*='slider']", "[class*='swiper']",
    ".nav", ".navbar", ".navigation", ".menu", ".breadcrumb", ".breadcrumbs",
    ".icon", "[class*='icon-']", "[class*='-icon']", "i.fa", "i.fas",
    "i.fab", "i.far", "svg",
    # OneTrust cookie consent (used by teg.ie) plus generic cookie/consent banners.
    "#onetrust-consent-sdk", "#onetrust-banner-sdk", "#onetrust-pc-sdk",
    ".onetrust-pc-dark-filter", ".ot-sdk-container",
    "[class*='cookie']", "[id*='cookie']",
    "[class*='consent']", "[id*='consent']",
])
