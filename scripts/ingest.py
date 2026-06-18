"""Command-line entry point for the full ingestion pipeline.

Runs crawl -> language -> chunk -> index in one shot.

    python -m scripts.ingest --max-depth 2 --recreate
"""

from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401

from app.core.logging import configure_logging
from app.pipeline.ingestion import IngestionConfig
from app.services import ingestion_service


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
    )

    result = ingestion_service.ingest(config)
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
