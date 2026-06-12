import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.pipeline.embedding.config import get_embedding_settings
from app.pipeline.embedding.models import IndexSummary, SearchResult
from app.pipeline.embedding.retriever import HybridRetriever
from app.pipeline.embedding_pipeline import run_indexing

router = APIRouter()

_retriever: HybridRetriever | None = None


def _get_retriever() -> HybridRetriever:
    """Lazily build and cache the hybrid retriever across requests."""
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever.from_settings()
    return _retriever


class IndexRequest(BaseModel):
    input_file: str | None = Field(
        default=None,
        description="Path to chunked_data.json; defaults to the configured input path",
    )
    recreate: bool = Field(
        default=False,
        description="Drop and recreate the Qdrant collection before indexing",
    )


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    top_k: int = Field(default=10, ge=1, le=100)


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


@router.post("/index", response_model=IndexSummary)
async def index(request: IndexRequest) -> IndexSummary:
    settings = get_embedding_settings()
    input_path = Path(request.input_file) if request.input_file else settings.input_path

    if not input_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Chunked data file not found: {input_path}",
        )

    global _retriever
    _retriever = None  # invalidate cached retriever after (re)indexing

    try:
        return await asyncio.to_thread(
            run_indexing,
            settings=settings,
            input_path=input_path,
            recreate=request.recreate,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    try:
        retriever = await asyncio.to_thread(_get_retriever)
        results = await asyncio.to_thread(
            retriever.search,
            request.query,
            request.top_k,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"{exc} Run /embedding/index before searching.",
        ) from exc

    return SearchResponse(
        query=request.query,
        results=[SearchResult(**result) for result in results],
    )
