"""SQLAlchemy engine factory for the content registry."""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.config.database_settings import DatabaseSettings, get_database_settings


@lru_cache(maxsize=1)
def create_database_engine(
    settings: DatabaseSettings | None = None,
) -> Engine:
    """Return a cached SQLAlchemy engine using settings from ``.env``."""
    settings = settings or get_database_settings()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
    )
