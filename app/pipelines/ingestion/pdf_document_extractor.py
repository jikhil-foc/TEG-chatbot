"""PDF crawl stage: fetch discovered PDFs and extract their text in memory."""

from __future__ import annotations

import asyncio
from io import BytesIO

import httpx
import pypdf

from app.pipelines.ingestion.crawl_settings import PDF_FETCH_TIMEOUT, PDF_MAX_CONCURRENT
from app.pipelines.ingestion.crawled_page import CrawledPage
from app.services.language_detector import clean_markdown, detect_language_from_text


def _pdf_metadata(reader: pypdf.PdfReader) -> dict:
    """Map pypdf document metadata to a plain dict."""
    raw = reader.metadata
    if not raw:
        return {"page_count": len(reader.pages)}

    field_map = {
        "/Title": "title",
        "/Author": "author",
        "/Subject": "subject",
        "/Creator": "creator",
        "/Producer": "producer",
    }
    metadata = {"page_count": len(reader.pages)}
    for pdf_key, name in field_map.items():
        value = raw.get(pdf_key)
        if value:
            metadata[name] = str(value)
    return metadata


def _extract_pdf_text(pdf_bytes: bytes) -> tuple[str, dict]:
    """Parse PDF bytes in memory and return markdown text plus metadata."""
    reader = pypdf.PdfReader(BytesIO(pdf_bytes))
    pages_text: list[str] = []
    for page in reader.pages:
        pages_text.append(page.extract_text() or "")
    markdown = clean_markdown("\n\n".join(pages_text).strip())
    return markdown, _pdf_metadata(reader)


async def _fetch_pdf_from_url(
    client: httpx.AsyncClient,
    url: str,
    semaphore: asyncio.Semaphore,
) -> CrawledPage:
    """HTTP-fetch a PDF URL into memory and extract its text (no disk writes)."""
    async with semaphore:
        try:
            response = await client.get(url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
                return CrawledPage(
                    url=url,
                    content_type="pdf",
                    success=False,
                    error=f"Unexpected content type: {content_type or 'unknown'}",
                )
            markdown, metadata = await asyncio.to_thread(
                _extract_pdf_text, response.content
            )
            success = bool(markdown.strip())
            return CrawledPage(
                url=url,
                content_type="pdf",
                markdown=markdown,
                language=detect_language_from_text(markdown) if success else None,
                metadata=metadata,
                success=success,
                error=None if success else "No extractable text in PDF",
            )
        except httpx.HTTPStatusError as exc:
            return CrawledPage(
                url=url,
                content_type="pdf",
                success=False,
                error=f"HTTP {exc.response.status_code}",
            )
        except Exception as exc:
            return CrawledPage(
                url=url,
                content_type="pdf",
                success=False,
                error=str(exc),
            )


async def crawl_pdfs(pdf_urls: list[str]) -> list[CrawledPage]:
    """Extract text and metadata from PDF URLs via in-memory HTTP fetch."""
    if not pdf_urls:
        return []

    semaphore = asyncio.Semaphore(PDF_MAX_CONCURRENT)
    async with httpx.AsyncClient(
        timeout=PDF_FETCH_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": "TEG-Chatbot-Crawler/1.0"},
    ) as client:
        return list(
            await asyncio.gather(
                *(_fetch_pdf_from_url(client, url, semaphore) for url in pdf_urls)
            )
        )
