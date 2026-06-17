"""Command-line entry point for the chunking pipeline.

    python -m scripts.chunk
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import _bootstrap  # noqa: F401

from app.core.logging import configure_logging
from app.pipeline.chunk import INPUT_PATH, OUTPUT_PATH, run_pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chunk", description="Chunk crawled JSON.")
    parser.add_argument("--input", type=Path, default=INPUT_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--no-save", action="store_true", help="Do not write JSON output")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    configure_logging(args.verbose)
    output_path = None if args.no_save else args.output
    result = run_pipeline(args.input, output_path)
    print(json.dumps(asdict(result.summary), indent=2))
    if output_path is not None:
        print(f"Wrote chunks to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
