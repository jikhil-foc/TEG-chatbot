"""Application configuration."""

from app.config.app_settings import Settings, settings
from app.config.data_paths import (
    BM25_STATE_PATH,
    CHUNKED_DATA_PATH,
    CRAWLED_DATA_FILENAME,
    CRAWLED_DATA_PATH,
    DATA_DIR,
    PROJECT_ROOT,
    ensure_data_dir,
)
from app.config.embedding_settings import EmbeddingSettings, get_embedding_settings

__all__ = [
    "BM25_STATE_PATH",
    "CHUNKED_DATA_PATH",
    "CRAWLED_DATA_FILENAME",
    "CRAWLED_DATA_PATH",
    "DATA_DIR",
    "EmbeddingSettings",
    "PROJECT_ROOT",
    "Settings",
    "ensure_data_dir",
    "get_embedding_settings",
    "settings",
]
