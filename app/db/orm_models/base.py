"""SQLAlchemy declarative base for content registry ORM models."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all content registry tables."""
