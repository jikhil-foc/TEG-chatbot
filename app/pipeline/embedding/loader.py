"""Load pre-chunked JSON documents into LangChain ``Document`` objects.

The chunked JSON is a flat array produced by
:mod:`app.pipeline.chunk_pipeline`. Each record is mapped to a ``Document``
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


def _record_to_document(record: dict[str, Any], encoding_name: str) -> Document:
    content = record.get("content", "") or ""
    metadata = {
        "chunk_id": record["chunk_id"],
        "parent_chunk_id": record.get("parent_chunk_id", record["chunk_id"]),
        "url": record.get("url", ""),
        "title": record.get("title", ""),
        "content_type": record.get("content_type", ""),
        "header_path": record.get("header_path", []) or [],
        "token_count": count_tokens(content, encoding_name),
    }
    return Document(page_content=content, metadata=metadata)


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
