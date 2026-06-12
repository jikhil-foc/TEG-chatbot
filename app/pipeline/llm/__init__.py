"""LLM-backed question answering over the hybrid RAG retriever.

Pipeline: retrieve hybrid-search hits from Qdrant, rerank them with the
``BAAI/bge-reranker-v2-m3`` cross-encoder, then generate a grounded, cited
answer with OpenAI ``gpt-4o-mini``.
"""

from app.pipeline.llm.models import AnswerResult, Source
from app.pipeline.llm.pipeline import answer_question

__all__ = [
    "AnswerResult",
    "Source",
    "answer_question",
]
