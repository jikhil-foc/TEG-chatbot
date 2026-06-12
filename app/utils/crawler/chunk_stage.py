"""Chunking stage: split crawled markdown into hybrid, structure-aware chunks.

The pipeline combines three complementary strategies so each chunk is
semantically coherent, structurally aware and well-sized for retrieval:

1. **Header split** -- :class:`MarkdownHeaderTextSplitter` divides each page
   into sections by markdown heading, keeping headings attached to the text
   beneath them and producing a breadcrumb (e.g. ``"TEG Levels > Fees"``).
2. **Semantic split** -- within any oversized section, sentences are embedded
   with a local multilingual ``sentence-transformers`` model and the section is
   cut wherever the cosine distance between consecutive sentences spikes
   (percentile breakpoints), so splits land where the meaning shifts.
3. **Recursive cap** -- any remaining oversized segment is hard-capped with a
   :class:`RecursiveCharacterTextSplitter` (size limit + overlap).

A final pass cleans separator artifacts and merges undersized fragments so the
output contains no tiny, context-poor chunks. Chunking is per-page, so every
chunk keeps the provenance (``url``, ``language`` and page ``metadata``) of the
page it came from, plus its section breadcrumb.
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

import numpy as np

from app.utils.crawler.config import (
    CHUNK_MERGE_CEILING,
    CHUNK_MIN_SIZE,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_MODEL_NAME,
    MARKDOWN_HEADERS,
    OUTPUT_DIR,
    OUTPUT_FILENAME,
    SEMANTIC_BREAKPOINT_PERCENTILE,
)
from app.utils.crawler.models import Chunk, CrawledPage

# Leading whitespace/punctuation left behind when a sentence-level split lands
# mid-sentence (e.g. a chunk starting with ``". These descriptions..."``).
_LEADING_ARTIFACT_RE = re.compile(r"^[\s.,;:)\]]+")
# Collapse runs of 3+ newlines down to a single blank line.
_EXTRA_BLANK_LINES_RE = re.compile(r"\n{3,}")
# Sentence/segment boundaries: end-of-sentence punctuation followed by
# whitespace, or a blank line (paragraph / markdown block break).
_SENTENCE_BOUNDARY_RE = re.compile(r"[.!?]\s+|\n{2,}")

# Lazy singletons: the embedding model is expensive to construct (and may
# download weights on first use), so build it once and reuse across all pages.
_model = None
_recursive_splitter = None
_header_splitter = None


def _get_model():
    """Return a cached multilingual ``sentence-transformers`` model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def _get_recursive_splitter():
    """Return a cached markdown-aware recursive splitter (size cap + overlap)."""
    global _recursive_splitter
    if _recursive_splitter is None:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        _recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""],
        )
    return _recursive_splitter


def _get_header_splitter():
    """Return a cached markdown header splitter that keeps heading metadata."""
    global _header_splitter
    if _header_splitter is None:
        from langchain_text_splitters import MarkdownHeaderTextSplitter

        _header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=MARKDOWN_HEADERS,
            strip_headers=True,
        )
    return _header_splitter


def _clean(text: str) -> str:
    """Trim whitespace and strip leading separator artifacts from a chunk."""
    text = _EXTRA_BLANK_LINES_RE.sub("\n\n", text).strip()
    return _LEADING_ARTIFACT_RE.sub("", text).strip()


def _breadcrumb(metadata: dict) -> str:
    """Build a ``"h1 > h2 > h3"`` breadcrumb from header-split metadata."""
    parts = [metadata.get(name) for _, name in MARKDOWN_HEADERS]
    return " > ".join(part.strip() for part in parts if part and part.strip())


def _sentence_spans(text: str) -> list[tuple[int, int]]:
    """Return ``(start, end)`` offsets covering ``text`` at sentence boundaries.

    Working with offsets (rather than split strings) lets us slice the original
    text back out, preserving its markdown formatting such as tables and lists.
    """
    spans: list[tuple[int, int]] = []
    start = 0
    for match in _SENTENCE_BOUNDARY_RE.finditer(text):
        spans.append((start, match.end()))
        start = match.end()
    if start < len(text):
        spans.append((start, len(text)))
    return spans


def _semantic_split(text: str) -> list[str]:
    """Split ``text`` at points where consecutive-sentence meaning shifts.

    Sentences are embedded and the cosine distance between each adjacent pair is
    computed; a break is inserted wherever a distance exceeds the configured
    percentile. Original substrings are sliced out so formatting is preserved.
    """
    spans = _sentence_spans(text)
    if len(spans) <= 1:
        return [text.strip()] if text.strip() else []

    sentences = [text[start:end].strip() for start, end in spans]
    embeddings = _get_model().encode(
        sentences,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    embeddings = np.asarray(embeddings)
    # Cosine similarity of unit vectors is their dot product; distance = 1 - sim.
    similarities = np.sum(embeddings[:-1] * embeddings[1:], axis=1)
    distances = 1.0 - similarities

    threshold = float(np.percentile(distances, SEMANTIC_BREAKPOINT_PERCENTILE))

    groups: list[list[int]] = [[0]]
    for i, distance in enumerate(distances):
        if distance > threshold:
            groups.append([i + 1])
        else:
            groups[-1].append(i + 1)

    segments: list[str] = []
    for group in groups:
        seg_start = spans[group[0]][0]
        seg_end = spans[group[-1]][1]
        segment = text[seg_start:seg_end].strip()
        if segment:
            segments.append(segment)
    return segments


def _size_split(text: str) -> list[str]:
    """Split one section's body via semantic boundaries, then a hard size cap."""
    if len(text) <= CHUNK_SIZE:
        return [text]

    pieces: list[str] = []
    for segment in _semantic_split(text):
        segment = _clean(segment)
        if not segment:
            continue
        if len(segment) <= CHUNK_SIZE:
            pieces.append(segment)
        else:
            pieces.extend(
                cleaned
                for piece in _get_recursive_splitter().split_text(segment)
                if (cleaned := _clean(piece))
            )
    return pieces


def _merge_small(pieces: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Merge adjacent ``(breadcrumb, text)`` pieces when one is undersized.

    A piece is folded into its predecessor whenever either is shorter than
    :data:`CHUNK_MIN_SIZE` and the combined length stays within
    :data:`CHUNK_MERGE_CEILING`. This removes lone headings and stray fragments
    without producing oversized chunks.
    """
    merged: list[tuple[str, str]] = []
    for breadcrumb, text in pieces:
        if merged:
            prev_breadcrumb, prev_text = merged[-1]
            either_small = (
                len(prev_text) < CHUNK_MIN_SIZE or len(text) < CHUNK_MIN_SIZE
            )
            fits = len(prev_text) + len(text) + 2 <= CHUNK_MERGE_CEILING
            if either_small and fits:
                merged[-1] = (prev_breadcrumb or breadcrumb, f"{prev_text}\n\n{text}")
                continue
        merged.append((breadcrumb, text))
    return merged


def _split_page(text: str) -> list[tuple[str, str]]:
    """Split a page's markdown into ``(breadcrumb, text)`` chunk pieces."""
    pieces: list[tuple[str, str]] = []
    for section in _get_header_splitter().split_text(text):
        breadcrumb = _breadcrumb(section.metadata)
        body = _clean(section.page_content)
        if not body:
            continue
        for segment in _size_split(body):
            if segment:
                pieces.append((breadcrumb, segment))
    return _merge_small(pieces)


def chunk_pages(pages: list[CrawledPage]) -> list[Chunk]:
    """Chunk a list of crawled pages into hybrid, structure-aware chunks.

    Pages that failed to crawl (``success=False``) or have empty markdown are
    skipped and produce no chunks. Each chunk's text is prefixed with its
    section breadcrumb (when available) to preserve heading context.
    """
    chunks: list[Chunk] = []

    for page in pages:
        if not page.success:
            continue
        text = (page.markdown or "").strip()
        if not text:
            continue

        for index, (breadcrumb, body) in enumerate(_split_page(text)):
            contextual_text = f"{breadcrumb}\n\n{body}" if breadcrumb else body
            chunks.append(
                Chunk(
                    chunk_id=str(uuid.uuid4()),
                    source_url=page.url,
                    content_type=page.content_type,
                    language=page.language,
                    chunk_index=index,
                    text=contextual_text,
                    char_count=len(contextual_text),
                    section=breadcrumb or None,
                    metadata=dict(page.metadata),
                )
            )

    return chunks


def chunk_crawled_data(
    input_path: Path = OUTPUT_DIR / OUTPUT_FILENAME,
) -> list[Chunk]:
    """Read a saved ``crawled-data.json`` file and chunk its pages.

    Useful for running the chunking stage independently of a live crawl.
    """
    payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
    pages = [CrawledPage(**page) for page in payload.get("pages", [])]
    return chunk_pages(pages)
