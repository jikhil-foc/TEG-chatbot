"""ORM model for crawled pages in the content registry."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.orm_models.base import Base


class PageRecord(Base):
    """A single crawled page (HTML or PDF)."""

    __tablename__ = "pages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_type: Mapped[str] = mapped_column(String(16), nullable=False)
    language: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_crawled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    sections: Mapped[list["SectionRecord"]] = relationship(
        "SectionRecord",
        back_populates="page",
        cascade="all, delete-orphan",
    )
