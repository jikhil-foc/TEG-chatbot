"""External system integrations for the RAG pipeline.

Wraps OpenAI (embeddings + chat), Cohere reranking, Qdrant hybrid storage,
BM25 sparse encoding, and crawl-time language detection behind a stable import
surface for pipeline nodes and API routes.
"""

from app.services.bm25_encoder import BM25SparseEmbeddings
from app.services.cohere_reranker import rerank
from app.services.grounded_answer import build_context, generate_answer, generate_answer_stream
from app.services.language_detector import (
    detect_language,
    detect_language_from_text,
    detect_query_language,
)
from app.services.openai_chat import build_chat_model
from app.services.openai_embeddings import build_dense_embeddings
from app.services.qdrant_vector_store import QdrantService

__all__ = [
    "BM25SparseEmbeddings",
    "QdrantService",
    "build_chat_model",
    "build_context",
    "build_dense_embeddings",
    "detect_language",
    "detect_language_from_text",
    "detect_query_language",
    "generate_answer",
    "generate_answer_stream",
    "rerank",
]
