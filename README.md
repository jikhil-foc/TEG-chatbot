# TEG Chatbot API

FastAPI backend for the TEG chatbot.

## Setup

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
```

### Qdrant (required for `/ask` and search)

The API stores embeddings in [Qdrant](https://qdrant.tech/). Start it locally before indexing or asking questions:

```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

Default URL: `http://localhost:6333` (override with `QDRANT_URL` in `.env`).

## Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | API info |
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/chat` | Send a chat message |
| POST | `/api/v1/crawl` | Crawl the website to JSON |
| POST | `/api/v1/chunk` | Chunk crawled JSON |
| POST | `/api/v1/embedding/index` | Index chunks into Qdrant |
| POST | `/api/v1/embedding/search` | Hybrid search |
| POST | `/api/v1/pipeline/ingest` | Run the full crawl→index pipeline |
| POST | `/api/v1/ask` | Ask a question (RAG, streamed via SSE) |

## Pipeline CLIs

```bash
python -m scripts.crawl --max-depth 2 --max-pages 200
python -m scripts.chunk
python -m scripts.embedding index --recreate
python -m scripts.embedding search --query "TEG levels" --top-k 5
python -m scripts.ingest --recreate          # full pipeline
```

## Tests

```bash
pytest
```

## Project structure

```
app/
├── main.py                    # FastAPI entry point
├── api/                       # HTTP layer (v1 routes, dependencies)
├── application/               # API facades (teg_qa_facade, teg_ingest_facade)
├── graphs/                    # LangGraph orchestration (QA + ingest)
├── nodes/
│   ├── ingestion/             # Ingest graph steps (crawl, chunk, index)
│   ├── retrieval/             # QA graph steps (retrieve, rerank, answer)
│   └── shared/                # Pure helpers (citations, relevance gate)
├── pipelines/
│   ├── ingestion/             # Crawl, chunk, indexing jobs
│   └── retrieval/             # Hybrid retriever, chunk loader
├── services/                  # External integrations (OpenAI, Cohere, Qdrant, BM25)
├── prompts/                   # LLM prompt templates
├── models/                    # Pydantic request/response models
├── config/                    # Settings and data paths
├── utils/                     # Logging, LangSmith tracing, language helpers
├── qa/                        # QA support (streaming, query analysis, session)
└── tools/                     # Agent tools (placeholder)

data/                          # runtime JSON artifacts (gitignored)
scripts/                       # CLI entry points
tests/                         # pytest suite
frontend/                      # React chat widget
```
