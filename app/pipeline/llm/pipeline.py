"""Question-answering orchestrator.

Thin wrapper that delegates to the QA LangGraph workflow in
:mod:`app.pipeline.qa.graph`, preserving the original :func:`answer_question`
signature and :class:`AnswerResult` contract for existing callers.
"""

from __future__ import annotations

from app.pipeline.embedding.config import EmbeddingSettings
from app.pipeline.embedding.retriever import HybridRetriever
from app.pipeline.llm.models import AnswerResult


def answer_question(
    query: str,
    top_k: int = 10,
    rerank_top_n: int = 5,
    retriever: HybridRetriever | None = None,
    settings: EmbeddingSettings | None = None,
) -> AnswerResult:
    """Answer ``query`` end-to-end over the indexed corpus.

    Runs the QA LangGraph workflow: detect language, hybrid retrieval, Cohere
    rerank, relevance gate (with fallback), grounded answer generation,
    citation extraction, and an LLM validation retry loop.
    """
    # Imported lazily to avoid a circular import: ``app.pipeline.qa.graph``
    # imports ``app.pipeline.llm`` modules, whose package __init__ imports this
    # module.
    from app.pipeline.qa.graph import run_qa_pipeline

    return run_qa_pipeline(
        query,
        top_k=top_k,
        rerank_top_n=rerank_top_n,
        retriever=retriever,
        settings=settings,
    )
