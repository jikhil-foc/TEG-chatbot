# Architecture Overview

Layered backend for the TEG chatbot RAG system.

## Layers

| Layer | Responsibility | Key packages |
|-------|----------------|--------------|
| **API** | HTTP routes, SSE streaming | `app/api/` |
| **Application** | Route-facing facades | `app/application/` |
| **Graphs** | LangGraph wiring only | `app/graphs/` |
| **Nodes** | Business steps per graph | `app/nodes/ingestion/`, `app/nodes/retrieval/` |
| **Pipelines** | Multi-step jobs | `app/pipelines/` |
| **Services** | Single vendor/store | `app/services/` |
| **Prompts** | LLM prompt strings | `app/prompts/` |

## Dependency rule

```
api → application → graphs → nodes → pipelines → services
```

No upward imports.

## Graphs

- **QA RAG** (`graphs/qa_rag_graph.py`): detect language → analyze query → hybrid retrieve → Cohere rerank → grounded answer → citations → validation loop.
- **Ingest** (`graphs/teg_ingest_graph.py`): crawl → enrich languages → chunk → index in Qdrant.

## Node packages

- `nodes/ingestion/` — 4 nodes for the ingest graph
- `nodes/retrieval/` — 13 nodes for the QA graph
- `nodes/shared/` — citation parsing, relevance gate, canned responses

## External services

- **OpenAI** — embeddings and chat (`services/openai_*`)
- **Cohere** — reranking (`services/cohere_reranker.py`)
- **Qdrant** — vector store (`services/qdrant_vector_store.py`)
- **BM25** — sparse encoder (`services/bm25_encoder.py`)

## Further reading

- [TEG ingestion pipeline](teg-ingestion-pipeline.md)
- [TEG QA retrieval pipeline](teg-qa-retrieval-pipeline.md)
