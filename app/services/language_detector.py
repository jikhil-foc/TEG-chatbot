"""Markdown cleanup and language detection for crawl results."""

from __future__ import annotations

import re

# Markdown links with no visible text, e.g. ``[](https://...)``. These are
# left behind when an icon/image-only anchor has its image stripped, so they
# carry no readable content and should be dropped.
_EMPTY_LINK_RE = re.compile(r"\[\]\([^)]*\)")
# A list bullet left empty after its only content (an empty link) was removed.
_EMPTY_BULLET_RE = re.compile(r"^[ \t]*[*+-][ \t]*$", re.MULTILINE)
# Three or more consecutive newlines collapse down to a single blank line.
_EXTRA_BLANK_LINES_RE = re.compile(r"\n{3,}")

# Captures the value of the ``lang`` attribute on the opening ``<html>`` tag,
# e.g. ``<html lang="ga">`` or ``<html dir="ltr" lang="en-IE">``.
_HTML_LANG_RE = re.compile(
    r"<html\b[^>]*?\blang\s*=\s*[\"']?([a-zA-Z][a-zA-Z-]*)", re.IGNORECASE
)

# Maps an ISO 639-1 primary language subtag to a human-readable name.
_LANG_NAMES = {"ga": "Irish", "en": "English"}

# Tokenises words while keeping accented vowels (the Irish síneadh fada) so
# fada-bearing words are counted as single tokens rather than split apart.
_WORD_RE = re.compile(r"[a-zà-ÿáéíóú]+", re.IGNORECASE)

# Minimum number of word tokens before a text-based guess is trusted. Below
# this, stopword counts are too noisy to be reliable, so we return ``None``.
_MIN_TOKENS = 20

# User queries are much shorter than crawled pages; a lower bar is enough when
# combined with síneadh fada (Irish accent marks) as an extra signal.
_MIN_QUERY_TOKENS = 3

# Irish vowels with síneadh fada — rare in English prose, strong Irish signal.
_FADA_RE = re.compile(r"[áéíóú]", re.IGNORECASE)

# High-frequency Irish function words (articles, conjunctions, prepositions,
# pronouns, common verb forms). These barely overlap with English, which makes
# them a strong signal for distinguishing the two languages.
_IRISH_STOPWORDS = frozenset({
    "agus", "an", "na", "go", "le", "ar", "do", "de", "sa", "is", "ní", "níl",
    "tá", "atá", "seo", "sin", "chun", "don", "dá", "ach", "mar", "nó", "ó",
    "faoi", "roimh", "thar", "idir", "gach", "aon", "ag", "anseo", "siad",
    "sé", "sí", "muid", "sinn", "bhfuil", "raibh", "beidh", "ina", "lena",
    "uile", "féin", "cuid", "leis", "agat", "againn", "acu", "orthu",
    # Common in short user questions
    "cé", "cad", "conas", "cén", "cá", "más", "má", "gur", "nach", "dar",
    "ceist", "freagra", "dírithe", "scrúdú", "scrúduithe",
})

# High-frequency English function words. Note ``an`` is intentionally omitted
# because it is also a very common Irish word (the definite article) and would
# otherwise bias scoring toward English. Question words and auxiliaries shared
# with Irish (e.g. ``do``) are included so short English queries are not
# misclassified when only one ambiguous token would otherwise score for Irish.
_ENGLISH_STOPWORDS = frozenset({
    "the", "and", "of", "to", "in", "is", "are", "was", "were", "for", "with",
    "on", "as", "by", "at", "this", "that", "from", "or", "be", "it", "not",
    "have", "has", "had", "will", "which", "you", "we", "they", "their", "our",
    "all", "can", "but", "more", "about", "if", "out", "up", "your", "these",
    # Common in short English user questions
    "a", "i", "me", "my", "do", "does", "did", "how", "what", "when", "where",
    "why", "who", "am",
})

# Minimum Irish-vs-English stopword margin before a query language guess is
# trusted; weaker signals default to ``None`` (English in the QA pipeline).
_QUERY_SCORE_MARGIN = 2


def clean_markdown(text: str) -> str:
    """Strip empty/icon-only links and the blank bullets they leave behind."""
    if not text:
        return text
    text = _EMPTY_LINK_RE.sub("", text)
    text = _EMPTY_BULLET_RE.sub("", text)
    text = _EXTRA_BLANK_LINES_RE.sub("\n\n", text)
    return text


def to_markdown(result) -> str:
    """Extract plain markdown text from a crawl4ai result object."""
    md = getattr(result, "markdown", None)
    if md is None:
        return ""
    raw = getattr(md, "raw_markdown", None)
    text = raw if raw is not None else str(md)
    return clean_markdown(text)


def _score_language(tokens: list[str], *, include_fada: bool) -> tuple[int, int]:
    """Return Irish and English hit counts for tokenised text."""
    irish = sum(t in _IRISH_STOPWORDS for t in tokens)
    if include_fada:
        irish += sum(1 for t in tokens if _FADA_RE.search(t))
    english = sum(t in _ENGLISH_STOPWORDS for t in tokens)
    return irish, english


def _language_from_scores(irish: int, english: int) -> str | None:
    """Return the winning language, or ``None`` when scores are tied or zero."""
    if irish == 0 and english == 0:
        return None
    if irish == english:
        return None
    return "Irish" if irish > english else "English"


def _language_from_query_scores(irish: int, english: int) -> str | None:
    """Like :func:`_language_from_scores` but requires a clear margin for queries."""
    if irish == 0 and english == 0:
        return None
    if irish == english:
        return None
    if abs(irish - english) < _QUERY_SCORE_MARGIN:
        return None
    return "Irish" if irish > english else "English"


def detect_language_from_text(text: str) -> str | None:
    """Guess Irish vs English by counting language-specific function words.

    Tokenises ``text`` and tallies how many tokens are common Irish stopwords
    versus common English stopwords; the higher count wins. Returns ``None``
    when the text is too short to judge (fewer than ``_MIN_TOKENS`` tokens) or
    when neither language scores any hits.
    """
    if not text:
        return None
    tokens = [t.lower() for t in _WORD_RE.findall(text)]
    if len(tokens) < _MIN_TOKENS:
        return None
    return _language_from_scores(*_score_language(tokens, include_fada=False))


def detect_query_language(text: str) -> str | None:
    """Guess Irish vs English for short user queries.

    Uses a lower token threshold than :func:`detect_language_from_text` and
    treats síneadh fada (``áéíóú``) in tokens as an additional Irish signal.
    """
    if not text:
        return None
    tokens = [t.lower() for t in _WORD_RE.findall(text)]
    if len(tokens) < _MIN_QUERY_TOKENS:
        return None
    return _language_from_query_scores(*_score_language(tokens, include_fada=True))


def detect_language(result) -> str | None:
    """Read the ``<html lang>`` attribute and map it to a language name.

    Returns ``"Irish"`` for ``lang="ga"``, ``"English"`` for ``lang="en"``
    (region subtags like ``en-IE`` are accepted). When the attribute is
    missing or holds an unrecognised code, falls back to scoring the page's
    markdown text, returning ``None`` only if that is also inconclusive.
    """
    html = getattr(result, "html", None) or ""
    match = _HTML_LANG_RE.search(html)
    if match:
        primary = match.group(1).split("-", 1)[0].lower()
        name = _LANG_NAMES.get(primary)
        if name:
            return name
    return detect_language_from_text(to_markdown(result))
