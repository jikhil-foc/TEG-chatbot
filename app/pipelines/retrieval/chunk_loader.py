"""Load pre-chunked JSON documents into LangChain ``Document`` objects.

The chunked JSON is a flat array produced by
:mod:`app.pipelines.ingestion.langchain_page_chunker. Each record is mapped to a ``Document``
whose ``metadata`` carries exactly the fields required for indexing/retrieval,
with ``token_count`` computed locally via ``tiktoken`` (it is not present in the
source file).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import tiktoken
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

_encoder: tiktoken.Encoding | None = None


def _get_encoder(encoding_name: str) -> tiktoken.Encoding:
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding(encoding_name)
    return _encoder


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """Count tokens with a local tiktoken encoder (no model inference)."""
    return len(_get_encoder(encoding_name).encode(text, disallowed_special=()))


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    """Drop blanks and consecutive/repeated duplicates, preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = (item or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


def build_breadcrumb(title: str, header_path: list[str]) -> str:
    """Build a ``title > h1 > h2`` breadcrumb from the page title and headers.

    The page title and header path frequently overlap, so duplicates are
    removed to avoid noisy repetition in the embedded text.
    """
    parts = _dedupe_preserve_order([title, *(header_path or [])])
    return " > ".join(parts)


def build_contextualized_content(
    title: str,
    header_path: list[str],
    content: str,
) -> str:
    """Prepend the section breadcrumb to a chunk so it is self-describing.

    A standalone table or short paragraph often omits the words that the user
    searches for (e.g. "fee"); prefixing the heading hierarchy makes the chunk
    retrievable on its own for both dense and sparse (BM25) search.
    """
    breadcrumb = build_breadcrumb(title, header_path)
    if breadcrumb:
        return f"{breadcrumb}\n\n{content}"
    return content


def _record_to_document(record: dict[str, Any], encoding_name: str) -> Document:
    raw_content = record.get("content", "") or ""
    title = record.get("title", "") or ""
    header_path = record.get("header_path", []) or []
    page_content = build_contextualized_content(title, header_path, raw_content)
    metadata = {
        "chunk_id": record["chunk_id"],
        "parent_chunk_id": record.get("parent_chunk_id", record["chunk_id"]),
        "url": record.get("url", ""),
        "title": title,
        "content_type": record.get("content_type", ""),
        "header_path": header_path,
        "chunk_index": record.get("chunk_index", 0),
        # Original block text (without breadcrumb) so a parent section can be
        # reassembled cleanly at retrieval time from its child chunks.
        "raw_content": raw_content,
        "token_count": count_tokens(page_content, encoding_name),
    }
    language = (record.get("language") or "").strip()
    if language:
        metadata["language"] = language
    return Document(page_content=page_content, metadata=metadata)


def load_documents(
    path: Path,
    encoding_name: str = "cl100k_base",
) -> list[Document]:
    """Load chunked JSON from ``path`` and return LangChain ``Document`` objects.

    Records with empty content are skipped. Raises ``FileNotFoundError`` if the
    file is missing and ``ValueError`` if the payload is not a JSON array.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Chunked data file not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(
            f"Expected a JSON array of chunks in {path}, got {type(payload).__name__}"
        )

    documents: list[Document] = []
    skipped = 0
    for record in payload:
        if not (record.get("content") or "").strip():
            skipped += 1
            continue
        documents.append(_record_to_document(record, encoding_name))

    logger.info(
        "Loaded %d documents from %s (%d empty chunks skipped)",
        len(documents),
        path,
        skipped,
    )
    return documents
