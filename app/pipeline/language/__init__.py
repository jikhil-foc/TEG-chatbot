"""Post-crawl language detection/enrichment pipeline stage."""

from app.pipeline.language.detector import (
    DEFAULT_INPUT_PATH,
    LanguageSummary,
    run_language_detection,
)

__all__ = [
    "DEFAULT_INPUT_PATH",
    "LanguageSummary",
    "run_language_detection",
]
