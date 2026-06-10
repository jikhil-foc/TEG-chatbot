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

## Project structure

```
app/
├── main.py           # FastAPI app entry point
├── api/routes/       # API route handlers
└── core/config.py    # Settings from environment
```
