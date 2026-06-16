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
├── main.py                 # FastAPI app entry point
├── core/                   # config, logging, paths (single source of truth)
├── api/
│   ├── deps.py             # shared FastAPI dependencies
│   └── v1/
│       ├── router.py       # aggregates all v1 routers
│       └── routes/         # health, chat, crawl, chunk, embedding, pipeline, ask
├── schemas/                # Pydantic request/response models
├── services/               # thin orchestration between routes and pipeline
└── pipeline/               # one package per stage
    ├── crawl/              # website crawler stages
    ├── language/           # language detection/enrichment
    ├── chunk/              # LangChain chunking
    ├── embedding/          # dense + sparse indexing/retrieval (+ orchestrator)
    ├── ingestion/          # LangGraph crawl→index pipeline
    ├── qa/                 # LangGraph question-answering
    └── llm/                # chat model, answerer, reranker

data/                       # runtime JSON artifacts (gitignored)
scripts/                    # CLI entry points
tests/                      # pytest suite
```
