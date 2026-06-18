"""ORM model for indexed chunks in the content registry."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.orm_models.base import Base

if TYPE_CHECKING:
    from app.db.orm_models.section_record import SectionRecord


class ChunkRecord(Base):
    """A child chunk mirrored in Qdrant."""

    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    parent_chunk_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    vector_id: Mapped[str] = mapped_column(Text, nullable=False)

    section: Mapped["SectionRecord"] = relationship(
        "SectionRecord", back_populates="chunks"
    )
