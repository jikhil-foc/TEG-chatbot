import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.pipeline.embedding.retriever import HybridRetriever
from app.pipeline.llm.models import Source
from app.pipeline.llm.pipeline import answer_question

router = APIRouter()

_retriever: HybridRetriever | None = None


def _get_retriever() -> HybridRetriever:
    """Lazily build and cache the hybrid retriever across requests."""
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever.from_settings()
    return _retriever


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    top_k: int = Field(
        default=10, ge=1, le=100, description="Hybrid-search hits to retrieve"
    )
    rerank_top_n: int = Field(
        default=5, ge=1, le=50, description="Reranked hits to keep as context"
    )


class AskResponse(BaseModel):
    query: str
    answer: str
    sources: list[Source]


@router.post("", response_model=AskResponse)
async def ask(request: AskRequest) -> AskResponse:
    try:
        retriever = await asyncio.to_thread(_get_retriever)
        result = await asyncio.to_thread(
            answer_question,
            request.query,
            request.top_k,
            request.rerank_top_n,
            retriever,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"{exc} Run /embedding/index before asking questions.",
        ) from exc

    return AskResponse(
        query=request.query,
        answer=result.answer,
        sources=result.sources,
    )
