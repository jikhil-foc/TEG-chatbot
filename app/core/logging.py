"""Shared logging configuration helpers."""

from __future__ import annotations

import logging

_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


def configure_logging(verbose: bool = False) -> None:
    """Configure root logging once for CLI entry points."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format=_LOG_FORMAT,
    )
