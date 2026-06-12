"""Hybrid RAG indexing pipeline: orchestrator and CLI.

Indexes pre-chunked JSON into Qdrant using OpenAI dense embeddings
(``text-embedding-3-large``) and a rank-bm25 sparse encoder, enabling hybrid
(dense + sparse) retrieval.

Usage
-----
Index the default chunked data file::

    python -m app.pipeline.embedding_pipeline index

Recreate the collection from scratch::

    python -m app.pipeline.embedding_pipeline index --recreate

Run a hybrid search::

    python -m app.pipeline.embedding_pipeline search --query "TEG levels" --top-k 5

Requires ``OPENAI_API_KEY`` in the environment/.env and a reachable Qdrant
instance (defaults to ``http://localhost:6333``).
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from app.pipeline.embedding.config import EmbeddingSettings, get_embedding_settings
from app.pipeline.embedding.dense import build_dense_embeddings
from app.pipeline.embedding.loader import load_documents
from app.pipeline.embedding.models import IndexSummary
from app.pipeline.embedding.qdrant_store import QdrantService
from app.pipeline.embedding.retriever import HybridRetriever
from app.pipeline.embedding.sparse_bm25 import BM25SparseEmbeddings

logger = logging.getLogger(__name__)


def run_indexing(
    settings: EmbeddingSettings | None = None,
    input_path: Path | None = None,
    recreate: bool = False,
) -> IndexSummary:
    """Run the full indexing pipeline and return an :class:`IndexSummary`.

    Steps: load chunks -> fit + persist BM25 -> ensure collection -> batch
    upload dense + sparse vectors with metadata.
    """
    settings = settings or get_embedding_settings()
    input_path = input_path or settings.input_path

    documents = load_documents(input_path, settings.token_encoding)
    if not documents:
        raise ValueError(f"No indexable documents found in {input_path}")

    logger.info("Fitting BM25 sparse encoder on %d documents", len(documents))
    sparse = BM25SparseEmbeddings.fit(
        corpus=[doc.page_content for doc in documents],
        k1=settings.bm25_k1,
        b=settings.bm25_b,
    )
    sparse.save(settings.bm25_state_path)

    dense = build_dense_embeddings(settings)

    service = QdrantService(
        settings=settings,
        dense_embeddings=dense,
        sparse_embeddings=sparse,
    )
    recreated = service.ensure_collection(recreate=recreate)
    vector_store = service.build_vector_store()
    uploaded, batches = service.upload_documents(vector_store, documents)

    summary = IndexSummary(
        collection_name=settings.collection_name,
        total_documents=len(documents),
        uploaded=uploaded,
        batches=batches,
        recreated_collection=recreated,
    )
    logger.info("Indexing complete: %s", summary.model_dump())
    return summary


def run_search(
    query: str,
    top_k: int = 10,
    settings: EmbeddingSettings | None = None,
) -> list[dict]:
    """Convenience wrapper that builds a retriever and runs one search."""
    retriever = HybridRetriever.from_settings(settings)
    return retriever.search(query, top_k=top_k)


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="embedding_pipeline",
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

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

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
        results = run_search(args.query, top_k=args.top_k, settings=settings)
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
