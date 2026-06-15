"""Command-line interface for the hybrid RAG indexing/retrieval pipeline.

Index the default chunked data file::

    python -m scripts.embedding index

Recreate the collection from scratch::

    python -m scripts.embedding index --recreate

Run a hybrid search::

    python -m scripts.embedding search --query "TEG levels" --top-k 5

Requires ``OPENAI_API_KEY`` in the environment/.env and a reachable Qdrant
instance (defaults to ``http://localhost:6333``).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.logging import configure_logging
from app.pipeline.embedding.config import get_embedding_settings
from app.pipeline.embedding.orchestrator import run_indexing, run_search


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="embedding",
        description="Hybrid RAG indexing and retrieval over Qdrant.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="Index chunked JSON into Qdrant")
    index_parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Path to chunked_data.json (defaults to configured input_path)",
    )
    index_parser.add_argument(
        "--recreate",
        action="store_true",
        help="Drop and recreate the Qdrant collection before indexing",
    )

    search_parser = subparsers.add_parser("search", help="Run a hybrid search")
    search_parser.add_argument("--query", required=True, help="Search query text")
    search_parser.add_argument("--top-k", type=int, default=10, help="Number of hits")
    search_parser.add_argument(
        "--no-expand",
        action="store_true",
        help="Return matched child chunks only, without parent-section expansion",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    settings = get_embedding_settings()

    if args.command == "index":
        summary = run_indexing(
            settings=settings,
            input_path=args.input,
            recreate=args.recreate,
        )
        print(json.dumps(summary.model_dump(), indent=2))
        return 0

    if args.command == "search":
        results = run_search(
            args.query,
            top_k=args.top_k,
            settings=settings,
            expand_to_parent=not args.no_expand,
        )
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
