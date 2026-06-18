"""LangGraph workflow nodes for ingestion and QA.

Each node is a thin adapter: it reads graph state, delegates to a pipeline or
service, and returns a partial state update. Conditional routing lives in
:mod:`app.graphs.teg_ingest_graph` and :mod:`app.graphs.qa_rag_graph`.
"""

from app.nodes import ingestion, retrieval

__all__ = ["ingestion", "retrieval"]
