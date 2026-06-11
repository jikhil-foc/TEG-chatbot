"""Persistence stage: serialise crawled pages to JSON on disk."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from app.utils.crawler.config import OUTPUT_DIR, OUTPUT_FILENAME
from app.utils.crawler.models import CrawledPage


def save_pages_json(
    pages: list[CrawledPage],
    source_url: str,
    output_dir: Path = OUTPUT_DIR,
    filename: str = OUTPUT_FILENAME,
) -> Path:
    """Save crawled pages (markdown + metadata) as a JSON file in ``output_dir``.

    Writes to ``crawled-data.json`` by default and overwrites the file on each
    crawl. Returns the path of the written JSON file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc)

    payload = {
        "source_url": source_url,
        "crawled_at": timestamp.isoformat(),
        "total": len(pages),
        "pages": [asdict(page) for page in pages],
    }

    output_path = output_dir / filename
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return output_path
