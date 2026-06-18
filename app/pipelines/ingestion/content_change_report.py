"""Report describing section-level content changes after a crawl."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.pipelines.ingestion.langchain_page_chunker import ChildChunk
from app.pipelines.ingestion.page_section import PageSection


@dataclass
class ContentChangeReport:
    """Sections that changed, stayed the same, or were removed."""

    unchanged_section_ids: list[str] = field(default_factory=list)
    changed_sections: list[PageSection] = field(default_factory=list)
    removed_section_ids: list[str] = field(default_factory=list)
    removed_chunk_ids: list[str] = field(default_factory=list)
    changed_chunks: list[ChildChunk] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(
            self.changed_sections
            or self.removed_section_ids
            or self.removed_chunk_ids
        )
