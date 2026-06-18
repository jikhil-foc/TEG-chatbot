"""Delete all rows from the PostgreSQL content registry tables.

Usage:
    python clear_db.py --yes
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy import func, select

from app.config.database_settings import get_database_settings
from app.db.content_registry_repository import ContentRegistryRepository
from app.db.database_session import session_scope
from app.db.orm_models import ChunkRecord, PageRecord, SectionRecord


def _table_counts(session) -> dict[str, int]:
    return {
        "pages": session.scalar(select(func.count()).select_from(PageRecord)) or 0,
        "sections": session.scalar(select(func.count()).select_from(SectionRecord)) or 0,
        "chunks": session.scalar(select(func.count()).select_from(ChunkRecord)) or 0,
    }


def clear_content_registry(*, confirm: bool) -> int:
    settings = get_database_settings()
    print(f"Database: {settings.db_host}:{settings.db_port}/{settings.db_database}")

    with session_scope() as session:
        before = _table_counts(session)
        total = sum(before.values())

        if total == 0:
            print("Content registry is already empty.")
            return 0

        print(
            "Rows to delete — "
            f"pages: {before['pages']}, "
            f"sections: {before['sections']}, "
            f"chunks: {before['chunks']}"
        )

        if not confirm:
            print("Aborted. Re-run with --yes to delete all content registry data.")
            return 1

        ContentRegistryRepository(session).clear_content_registry()
        after = _table_counts(session)

    print(
        "Deleted content registry data — "
        f"pages: {before['pages']}, "
        f"sections: {before['sections']}, "
        f"chunks: {before['chunks']}"
    )
    assert after == {"pages": 0, "sections": 0, "chunks": 0}
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Delete all data from PostgreSQL content registry tables.",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Confirm deletion without an interactive prompt",
    )
    args = parser.parse_args(argv)
    return clear_content_registry(confirm=args.yes)


if __name__ == "__main__":
    raise SystemExit(main())
