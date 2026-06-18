"""Centralized filesystem paths for the application."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"

CRAWLED_DATA_FILENAME = "crawled-data.json"
CRAWLED_DATA_PATH = DATA_DIR / CRAWLED_DATA_FILENAME
CHUNKED_DATA_PATH = DATA_DIR / "chunked_data.json"
BM25_STATE_PATH = DATA_DIR / "bm25_state.json"


def ensure_data_dir() -> Path:
    """Create the data directory if it does not yet exist and return it."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR
