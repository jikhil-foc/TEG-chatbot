"""Standalone LangChain chunking pipeline for crawled website data.

Uses deterministic LangChain text splitters only (no LLM or embedding models).
HTML pages follow a parent-child hierarchy: markdown headers -> parent chunks
(blocks merged up to ~2000 tokens) -> child chunks (one content block each).
PDF pages use character-based recursive splitting. Only child chunks are emitted
to ``chunked_data.json``.

Chunks are assembled from *semantic content blocks*: headings, paragraphs (each
newline-separated line), tables, lists and fenced code blocks. Each content
block is atomic and is never split across chunks. Child chunks are emitted one
per content block (paragraph-wise), so a paragraph, table, list or code block
always lands in exactly one child chunk. Parent chunks merge consecutive blocks
greedily up to the parent token target for retrieval context. ``tiktoken``
(``cl100k_base``) is used only as a local token counter for parent merging; it
does not load or call any model.

This module is independent of the website crawler; it reads the JSON output
produced by :mod:`app.pipeline.crawl`.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

import tiktoken
from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from app.core.paths import CHUNKED_DATA_PATH, CRAWLED_DATA_PATH

INPUT_PATH = CRAWLED_DATA_PATH
OUTPUT_PATH = CHUNKED_DATA_PATH

_MARKDOWN_HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]

# Parent token target. Treated as a soft ceiling: a single content block that
# exceeds it is kept intact rather than split. Child chunks are emitted one per
# content block (paragraph-wise) and so are not bounded by a token target.
_PARENT_CHUNK_SIZE = 2000

_PDF_CHUNK_SIZE = 800
_PDF_CHUNK_OVERLAP = 0

_TOKEN_ENCODING = "cl100k_base"

# Content-block detection (markdown). Headings are atomic single lines; tables
# are runs of pipe rows; lists are runs of list items plus indented
# continuations; fenced code blocks span their opening/closing fences.
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s")
_FENCE_RE = re.compile(r"^\s*(```+|~~~+)")
_LIST_RE = re.compile(r"^\s*([-*+]|\d+[.)])\s+")

_header_splitter: MarkdownHeaderTextSplitter | None = None
_pdf_splitter: RecursiveCharacterTextSplitter | None = None
_encoder: tiktoken.Encoding | None = None


@dataclass
class ChildChunk:
    """A single child-level chunk ready for JSON serialisation or vector ingestion."""

    chunk_id: str
    parent_chunk_id: str
    url: str
    title: str
    language: str | None
    content_type: str
    header_path: list[str]
    chunk_level: str
    chunk_index: int
    content: str


@dataclass
class ChunkingSummary:
    """Aggregate counts describing the result of a chunking run."""

    total_pages_loaded: int
    html_pages_processed: int
    html_parent_chunks: int
    html_child_chunks: int
    pdf_pages_processed: int
    pdf_child_chunks: int
    total_child_chunks: int


@dataclass
class PipelineResult:
    """Documents produced by the pipeline plus the run summary."""

    documents: list[Document]
    summary: ChunkingSummary


def load(path: Path = INPUT_PATH) -> list[dict]:
    """Load the crawled JSON file and return its list of page dicts."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload.get("pages", [])


def _get_encoder() -> tiktoken.Encoding:
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding(_TOKEN_ENCODING)
    return _encoder


def _token_len(text: str) -> int:
    """Count tokens with a local tiktoken encoder (no model inference)."""
    return len(_get_encoder().encode(text, disallowed_special=()))


def _get_header_splitter() -> MarkdownHeaderTextSplitter:
    global _header_splitter
    if _header_splitter is None:
        _header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=_MARKDOWN_HEADERS,
            strip_headers=False,
        )
    return _header_splitter


def _get_pdf_splitter() -> RecursiveCharacterTextSplitter:
    global _pdf_splitter
    if _pdf_splitter is None:
        _pdf_splitter = RecursiveCharacterTextSplitter(
            chunk_size=_PDF_CHUNK_SIZE,
            chunk_overlap=_PDF_CHUNK_OVERLAP,
            separators=["\n\n", "\n", ".", " ", ""],
        )
    return _pdf_splitter


def _is_table_line(line: str) -> bool:
    return "|" in line and bool(line.strip())


def split_into_blocks(text: str) -> list[str]:
    """Split markdown into atomic content blocks.

    Recognised blocks: fenced code blocks, headings, tables, lists and
    paragraphs. Each block is returned as a standalone string and is never
    broken further by the chunkers. Blank lines act as separators and are
    dropped between blocks.
    """
    lines = text.split("\n")
    blocks: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        fence = _FENCE_RE.match(line)
        if fence:
            marker = fence.group(1)[:3]
            buffer = [line]
            i += 1
            while i < n:
                buffer.append(lines[i])
                closed = lines[i].strip().startswith(marker)
                i += 1
                if closed:
                    break
            blocks.append("\n".join(buffer))
            continue

        if _HEADING_RE.match(line):
            blocks.append(line.rstrip())
            i += 1
            continue

        if _is_table_line(line):
            buffer = [line]
            i += 1
            while i < n and _is_table_line(lines[i]):
                buffer.append(lines[i])
                i += 1
            blocks.append("\n".join(buffer))
            continue

        if _LIST_RE.match(line):
            buffer = [line]
            i += 1
            while i < n and lines[i].strip() and (
                _LIST_RE.match(lines[i]) or lines[i].startswith((" ", "\t"))
            ):
                if _HEADING_RE.match(lines[i]) or _is_table_line(lines[i]):
                    break
                buffer.append(lines[i])
                i += 1
            blocks.append("\n".join(buffer))
            continue

        # Paragraph: each newline-separated line is its own atomic block.
        blocks.append(line.strip())
        i += 1

    return [block.strip() for block in blocks if block.strip()]


def merge_blocks(blocks: list[str], target_tokens: int) -> list[str]:
    """Greedily merge content blocks into chunks of at most ``target_tokens``.

    A block is never split. Consecutive blocks accumulate into the current
    chunk until adding the next block would exceed ``target_tokens``, at which
    point a new chunk is started. A block larger than ``target_tokens`` becomes
    its own (oversized) chunk, preserving content integrity.
    """
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for block in blocks:
        block_tokens = _token_len(block)
        if current and current_tokens + block_tokens > target_tokens:
            chunks.append("\n\n".join(current))
            current = []
            current_tokens = 0
        current.append(block)
        current_tokens += block_tokens

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def _header_path(metadata: dict) -> list[str]:
    """Build ordered header hierarchy from markdown header-split metadata."""
    return [metadata[key] for _, key in _MARKDOWN_HEADERS if metadata.get(key)]


def _child_to_document(chunk: ChildChunk) -> Document:
    """Map a flat child chunk to a LangChain ``Document`` for vector-store use."""
    return Document(
        page_content=chunk.content,
        metadata={
            "chunk_id": chunk.chunk_id,
            "parent_chunk_id": chunk.parent_chunk_id,
            "url": chunk.url,
            "title": chunk.title,
            "language": chunk.language,
            "content_type": chunk.content_type,
            "header_path": chunk.header_path,
            "chunk_level": chunk.chunk_level,
            "chunk_index": chunk.chunk_index,
        },
    )


def document_to_child_chunk(document: Document) -> ChildChunk:
    """Reconstruct a :class:`ChildChunk` from a pipeline ``Document``."""
    metadata = document.metadata
    return ChildChunk(
        chunk_id=metadata["chunk_id"],
        parent_chunk_id=metadata["parent_chunk_id"],
        url=metadata["url"],
        title=metadata.get("title", ""),
        language=metadata.get("language"),
        content_type=metadata["content_type"],
        header_path=metadata.get("header_path", []),
        chunk_level=metadata.get("chunk_level", "child"),
        chunk_index=metadata["chunk_index"],
        content=document.page_content,
    )


def split_html(pages: list[dict]) -> tuple[list[ChildChunk], int]:
    """Split HTML pages into parent-child chunks with header hierarchy metadata.

    Parents merge atomic content blocks up to the parent token target; children
    are emitted one per content block (paragraph-wise), so no paragraph, table,
    list or code block is ever split. Returns child chunks only and the total
    number of parent chunks produced.
    """
    header_splitter = _get_header_splitter()

    chunks: list[ChildChunk] = []
    parent_count = 0

    for page in pages:
        if page.get("content_type") != "html" or not page.get("success"):
            continue
        markdown = page.get("markdown") or ""
        if not markdown.strip():
            continue

        page_metadata = page.get("metadata", {})
        url = page.get("url", "")
        title = page_metadata.get("title", "")
        language = page.get("language")
        chunk_index = 0

        for section in header_splitter.split_text(markdown):
            header_path = _header_path(section.metadata)
            section_blocks = split_into_blocks(section.page_content)

            for parent_text in merge_blocks(section_blocks, _PARENT_CHUNK_SIZE):
                parent_text = parent_text.strip()
                if not parent_text:
                    continue

                parent_id = str(uuid.uuid4())
                parent_count += 1

                for child_text in split_into_blocks(parent_text):
                    child_text = child_text.strip()
                    if not child_text:
                        continue

                    chunks.append(
                        ChildChunk(
                            chunk_id=str(uuid.uuid4()),
                            parent_chunk_id=parent_id,
                            url=url,
                            title=title,
                            language=language,
                            content_type="html",
                            header_path=header_path,
                            chunk_level="child",
                            chunk_index=chunk_index,
                            content=child_text,
                        )
                    )
                    chunk_index += 1

    return chunks, parent_count


def split_pdf(pages: list[dict]) -> list[ChildChunk]:
    """Split PDF pages into fixed-size overlapping child chunks with flat metadata."""
    splitter = _get_pdf_splitter()
    chunks: list[ChildChunk] = []

    for page in pages:
        if page.get("content_type") != "pdf" or not page.get("success"):
            continue
        markdown = page.get("markdown") or ""
        if not markdown.strip():
            continue

        page_metadata = page.get("metadata", {})
        url = page.get("url", "")
        title = page_metadata.get("title", "")
        language = page.get("language")

        for chunk_index, text in enumerate(splitter.split_text(markdown)):
            text = text.strip()
            if not text:
                continue

            chunk_id = str(uuid.uuid4())
            chunks.append(
                ChildChunk(
                    chunk_id=chunk_id,
                    parent_chunk_id=chunk_id,
                    url=url,
                    title=title,
                    language=language,
                    content_type="pdf",
                    header_path=[],
                    chunk_level="child",
                    chunk_index=chunk_index,
                    content=text,
                )
            )

    return chunks


def run_pipeline(
    input_path: Path = INPUT_PATH,
    output_path: Path | None = OUTPUT_PATH,
) -> PipelineResult:
    """Run the full pipeline: load, split, merge, summarise and optionally save.

    ``input_path`` selects the crawled JSON to chunk. When ``output_path`` is
    given the merged child chunks are serialised there as a flat JSON array;
    pass ``None`` to skip writing. Returns a :class:`PipelineResult` containing
    the LangChain ``Document`` objects built from the child chunks (ready to
    pass to a vector store) and a :class:`ChunkingSummary` of run counts.
    """
    pages = load(input_path)

    html_pages = [
        page
        for page in pages
        if page.get("content_type") == "html"
        and page.get("success")
        and (page.get("markdown") or "").strip()
    ]
    pdf_pages = [
        page
        for page in pages
        if page.get("content_type") == "pdf"
        and page.get("success")
        and (page.get("markdown") or "").strip()
    ]

    html_chunks, html_parent_count = split_html(pages)
    pdf_chunks = split_pdf(pages)
    all_child_chunks = html_chunks + pdf_chunks
    documents = [_child_to_document(chunk) for chunk in all_child_chunks]

    summary = ChunkingSummary(
        total_pages_loaded=len(pages),
        html_pages_processed=len(html_pages),
        html_parent_chunks=html_parent_count,
        html_child_chunks=len(html_chunks),
        pdf_pages_processed=len(pdf_pages),
        pdf_child_chunks=len(pdf_chunks),
        total_child_chunks=len(all_child_chunks),
    )

    if output_path is not None:
        serialised = [asdict(chunk) for chunk in all_child_chunks]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(serialised, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return PipelineResult(documents=documents, summary=summary)


def main() -> PipelineResult:
    """Run the pipeline against the default input/output paths."""
    return run_pipeline()


if __name__ == "__main__":
    main()
