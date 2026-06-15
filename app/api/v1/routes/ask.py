import asyncio

from fastapi import APIRouter, HTTPException

from app.schemas.ask import AskRequest, AskResponse
from app.services import ask_service

router = APIRouter()


@router.post("", response_model=AskResponse)
async def ask(request: AskRequest) -> AskResponse:
    try:
        result = await asyncio.to_thread(
            ask_service.answer,
            request.query,
            request.top_k,
            request.rerank_top_n,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"{exc} Run /embedding/index before asking questions.",
        ) from exc

    return AskResponse(
        query=request.query,
        answer=result.answer,
        language=result.language,
        sources=result.sources,
    )
