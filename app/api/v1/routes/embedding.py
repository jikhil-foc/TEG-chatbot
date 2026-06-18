import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.pipelines.retrieval.retriever_cache import get_retriever, invalidate_retriever
from app.config.embedding_settings import get_embedding_settings
from app.models.embedding import IndexSummary, SearchResult
from app.pipelines.ingestion.indexing_job import run_indexing
from app.models.embedding import IndexRequest, SearchRequest, SearchResponse

router = APIRouter()


@router.post("/index", response_model=IndexSummary)
async def index(request: IndexRequest) -> IndexSummary:
    settings = get_embedding_settings()
    input_path = Path(request.input_file) if request.input_file else settings.input_path

    if not input_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Chunked data file not found: {input_path}",
        )

    invalidate_retriever()

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
        retriever = await asyncio.to_thread(get_retriever)
        results = await asyncio.to_thread(
            retriever.search,
            request.query,
            request.top_k,
            request.expand_to_parent,
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
