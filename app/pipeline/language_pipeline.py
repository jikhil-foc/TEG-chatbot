"""Post-crawl language enrichment for crawled website data.

Re-runs language detection on every page in ``crawled-data.json``, filling in
missing values and validating existing tags. This is a standalone pipeline step
used by the LangGraph ingestion graph between crawl and chunk.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.utils.crawler.config import OUTPUT_DIR, OUTPUT_FILENAME
from app.utils.crawler.text import detect_language_from_text

DEFAULT_INPUT_PATH = OUTPUT_DIR / OUTPUT_FILENAME


@dataclass
class LanguageSummary:
    """Aggregate counts describing a language-detection run."""

    total: int
    irish: int
    english: int
    unknown: int
    updated: int


def run_language_detection(
    input_path: Path | None = None,
    *,
    save: bool = True,
) -> LanguageSummary:
    """Detect or re-detect language for every page in the crawled JSON file.

    For each page, ``detect_language_from_text`` is run on the markdown body.
    When the detected value differs from the stored ``language`` field the page
    is updated. When ``save`` is True the file is written back in place.

    Returns a :class:`LanguageSummary` with per-language counts and the number
    of pages whose ``language`` field changed.
    """
    path = input_path or DEFAULT_INPUT_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    pages: list[dict] = payload.get("pages", [])

    irish = 0
    english = 0
    unknown = 0
    updated = 0

    for page in pages:
        markdown = page.get("markdown") or ""
        detected = detect_language_from_text(markdown)

        if detected == "Irish":
            irish += 1
        elif detected == "English":
            english += 1
        else:
            unknown += 1

        previous = page.get("language")
        if detected != previous:
            page["language"] = detected
            updated += 1

    if save:
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    return LanguageSummary(
        total=len(pages),
        irish=irish,
        english=english,
        unknown=unknown,
        updated=updated,
    )
