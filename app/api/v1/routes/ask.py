import asyncio
import json
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.ask import AskRequest
from app.services import ask_service

router = APIRouter()


def _format_sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@router.post("")
async def ask(request: AskRequest) -> StreamingResponse:
    try:
        await asyncio.to_thread(ask_service.ensure_index)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"{exc} Run /embedding/index before asking questions.",
        ) from exc
    except ask_service.QdrantUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    def event_stream() -> Iterator[str]:
        try:
            for event in ask_service.answer_stream(
                request.query,
                request.top_k,
                request.rerank_top_n,
            ):
                yield _format_sse(event)
        except Exception as exc:
            yield _format_sse({"type": "error", "message": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
