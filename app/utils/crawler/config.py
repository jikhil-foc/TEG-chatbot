"""Shared configuration and constants for the website crawler stages."""

from __future__ import annotations

from pathlib import Path

import httpx

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "output"
OUTPUT_FILENAME = "crawled-data.json"

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
