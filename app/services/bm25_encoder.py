"""BM25 sparse embeddings for Qdrant hybrid search.

``rank-bm25`` scores a query against a corpus; it does not natively emit
per-document sparse vectors. This module wraps it in a LangChain
:class:`~langchain_qdrant.SparseEmbeddings` implementation using the
well-known "BM25 as a dot product" split (as popularised by Pinecone):

* document vector values use the length-normalised, saturated term frequency
  ``tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl / avgdl))``;
* query vector values use the term IDF.

The dot product of a document and query sparse vector then approximates the
BM25 score. The fitted vocabulary, IDF table, average document length and
parameters are persisted to JSON so retrieval reuses the exact same state.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from pathlib import Path

from langchain_qdrant import SparseEmbeddings
from langchain_qdrant.sparse_embeddings import SparseVector
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Lowercase word-tokeniser used for both indexing and querying."""
    return _TOKEN_RE.findall(text.lower())


class BM25SparseEmbeddings(SparseEmbeddings):
    """A fitted BM25 sparse encoder compatible with ``QdrantVectorStore``.

    Construct via :meth:`fit` (from a corpus) or :meth:`load` (from persisted
    state). Calling :meth:`embed_documents` / :meth:`embed_query` before the
    encoder is fitted raises ``RuntimeError``.
    """

    def __init__(
        self,
        vocab: dict[str, int],
        idf: dict[str, float],
        avgdl: float,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self._vocab = vocab
        self._idf = idf
        self._avgdl = avgdl or 1.0
        self._k1 = k1
        self._b = b

    @classmethod
    def fit(
        cls,
        corpus: list[str],
        k1: float = 1.5,
        b: float = 0.75,
    ) -> "BM25SparseEmbeddings":
        """Fit the encoder on a text ``corpus`` and return a ready instance."""
        if not corpus:
            raise ValueError("Cannot fit BM25 on an empty corpus")

        tokenized = [tokenize(text) for text in corpus]
        bm25 = BM25Okapi(tokenized, k1=k1, b=b)

        # ``BM25Okapi`` exposes ``idf`` (token -> idf) and ``avgdl``.
        idf: dict[str, float] = {
            token: float(score) for token, score in bm25.idf.items()
        }
        vocab = {token: index for index, token in enumerate(sorted(idf))}

        logger.info(
            "Fitted BM25 sparse encoder: %d documents, vocab=%d, avgdl=%.2f",
            len(corpus),
            len(vocab),
            bm25.avgdl,
        )
        return cls(vocab=vocab, idf=idf, avgdl=float(bm25.avgdl), k1=k1, b=b)

    def _ensure_fitted(self) -> None:
        if not self._vocab:
            raise RuntimeError("BM25 encoder is not fitted; call fit() or load() first")

    def embed_documents(self, texts: list[str]) -> list[SparseVector]:
        self._ensure_fitted()
        return [self._embed_document(text) for text in texts]

    def embed_query(self, text: str) -> SparseVector:
        self._ensure_fitted()
        return self._embed_query(text)

    def _embed_document(self, text: str) -> SparseVector:
        tokens = tokenize(text)
        doc_len = len(tokens)
        counts = Counter(tokens)

        indices: list[int] = []
        values: list[float] = []
        for token, tf in counts.items():
            index = self._vocab.get(token)
            if index is None:
                continue
            denom = tf + self._k1 * (1 - self._b + self._b * doc_len / self._avgdl)
            weight = (tf * (self._k1 + 1)) / denom if denom else 0.0
            if weight:
                indices.append(index)
                values.append(weight)
        return SparseVector(indices=indices, values=values)

    def _embed_query(self, text: str) -> SparseVector:
        tokens = tokenize(text)
        indices: list[int] = []
        values: list[float] = []
        seen: set[int] = set()
        for token in tokens:
            index = self._vocab.get(token)
            if index is None or index in seen:
                continue
            weight = self._idf.get(token, 0.0)
            if weight:
                indices.append(index)
                values.append(float(weight))
                seen.add(index)
        return SparseVector(indices=indices, values=values)

    def save(self, path: Path) -> None:
        """Persist the fitted state to ``path`` as JSON."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "vocab": self._vocab,
            "idf": self._idf,
            "avgdl": self._avgdl,
            "k1": self._k1,
            "b": self._b,
        }
        path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        logger.info("Saved BM25 state to %s", path)

    @classmethod
    def load(cls, path: Path) -> "BM25SparseEmbeddings":
        """Load a previously fitted encoder from ``path``."""
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(
                f"BM25 state not found: {path}. Run indexing before retrieval."
            )
        state = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            vocab=state["vocab"],
            idf=state["idf"],
            avgdl=state["avgdl"],
            k1=state.get("k1", 1.5),
            b=state.get("b", 0.75),
        )
