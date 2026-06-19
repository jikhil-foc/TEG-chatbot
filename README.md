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

The API stores embeddings in [Qdrant](https://qdrant.tech/). Default URL: `http://localhost:6333` (override with `QDRANT_URL` in `.env`).

## Run (Docker — all services)

Start Qdrant, PostgreSQL, the FastAPI backend, and the Vite frontend with one command:

```bash
cp .env.example .env   # fill OPENAI_API_KEY and COHERE_API_KEY
docker compose up --build
```

| Service | URL |
|---------|-----|
| Chat UI | [http://localhost:5173](http://localhost:5173) |
| API docs | [http://localhost:8000/docs](http://localhost:8000/docs) |
| Qdrant dashboard | [http://localhost:6333/dashboard](http://localhost:6333/dashboard) |

Compose overrides `QDRANT_URL` to `http://qdrant:6333` and `DB_HOST` to `postgres` inside the backend container. Alembic migrations run automatically on backend startup. Your `.env` file must exist with API keys before starting.

PostgreSQL is exposed on host port **5433** (not 5432) so it does not conflict with a local PostgreSQL install. From host-side tools use `localhost:5433` with the same username/password/database as in `.env`. The API health check reports content-registry row counts from the database the backend actually uses.

The backend image includes Playwright Chromium for crawl/ingest endpoints. After changing the Dockerfile, rebuild with `docker compose up --build`.

## Run (manual)

Start Qdrant only:

```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

Start the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

Start the frontend (from `frontend/`):

```bash
npm install
npm run dev
```

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
