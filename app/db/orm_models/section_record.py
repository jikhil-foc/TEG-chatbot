"""ORM model for page sections in the content registry."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.orm_models.base import Base

if TYPE_CHECKING:
    from app.db.orm_models.chunk_record import ChunkRecord
    from app.db.orm_models.page_record import PageRecord


class SectionRecord(Base):
    """A header-delimited section within a crawled page."""

    __tablename__ = "sections"
    __table_args__ = (
        UniqueConstraint("page_id", "section_key", name="uq_sections_page_section_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pages.id", ondelete="CASCADE"), nullable=False
    )
    section_key: Mapped[str] = mapped_column(Text, nullable=False)
    header_path: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
        server_default=func.now(),
    )

    page: Mapped["PageRecord"] = relationship("PageRecord", back_populates="sections")
    chunks: Mapped[list["ChunkRecord"]] = relationship(
        "ChunkRecord",
        back_populates="section",
        cascade="all, delete-orphan",
    )
