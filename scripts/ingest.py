"""Command-line entry point for the full ingestion pipeline.

Runs crawl -> language -> chunk -> index in one shot.

    python -m scripts.ingest --max-depth 2 --recreate
"""

from __future__ import annotations

import argparse

if __package__:
    from scripts import _bootstrap  # noqa: F401
else:
    import _bootstrap  # noqa: F401

from app.utils.logging_config import configure_logging
from app.models.ingest_request import IngestionConfig
from app.application import teg_ingest_facade as ingestion_service


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ingest", description="Run full ingestion.")
    parser.add_argument("--url", default=None, help="Start URL (defaults to WEBSITE_URL)")
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--max-pages", type=int, default=500)
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF extraction")
    parser.add_argument("--include-external", action="store_true")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Drop and recreate the Qdrant collection before indexing",
    )
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Run full chunk/index and populate the PostgreSQL content registry",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Enable incremental section change detection",
    )
    parser.add_argument("--no-save", action="store_true", help="Do not write JSON output")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    configure_logging(args.verbose)
    config = IngestionConfig(
        url=args.url,
        max_depth=args.max_depth,
        max_pages=args.max_pages,
        include_pdf=not args.no_pdf,
        include_external=args.include_external,
        recreate=args.recreate,
        save_json=not args.no_save,
        incremental=args.incremental,
        baseline=args.baseline,
    )

    result = ingestion_service.ingest(config)
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
