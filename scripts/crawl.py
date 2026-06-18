"""Command-line entry point for the website crawler.

    python -m scripts.crawl --max-depth 2 --max-pages 200
"""

from __future__ import annotations

import argparse

if __package__:
    from scripts import _bootstrap  # noqa: F401
else:
    import _bootstrap  # noqa: F401

from app.config.app_settings import settings
from app.utils.logging_config import configure_logging
from app.pipelines.ingestion.teg_site_crawler import run_crawl, save_pages_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="crawl", description="Crawl a website to JSON.")
    parser.add_argument("--url", default=None, help="Start URL (defaults to WEBSITE_URL)")
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--max-pages", type=int, default=500)
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF extraction")
    parser.add_argument("--include-external", action="store_true")
    parser.add_argument("--no-save", action="store_true", help="Do not write JSON output")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    configure_logging(args.verbose)
    start_url = args.url or settings.website_url

    pages = run_crawl(
        url=start_url,
        max_depth=args.max_depth,
        max_pages=args.max_pages,
        include_pdf=not args.no_pdf,
        include_external=args.include_external,
        save_json=False,
    )

    if not args.no_save:
        output = save_pages_json(pages, source_url=start_url)
        print(f"Saved {len(pages)} pages to {output}")

    succeeded = sum(1 for page in pages if page.success)
    print(f"Crawled {len(pages)} resources ({succeeded} ok, {len(pages) - succeeded} failed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
