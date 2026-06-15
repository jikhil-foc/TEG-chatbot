import asyncio
import json
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.pipeline.chunk_pipeline import (
    INPUT_PATH,
    OUTPUT_PATH,
    run_pipeline,
)

router = APIRouter()


class ChunkRequest(BaseModel):
    input_file: str | None = Field(
        default=None,
        description="Path to crawled-data.json; defaults to the standard output file",
    )
    save_json: bool = True


class ChunkingSummaryModel(BaseModel):
    total_pages_loaded: int
    html_pages_processed: int
    html_parent_chunks: int
    html_child_chunks: int
    pdf_pages_processed: int
    pdf_child_chunks: int
    total_child_chunks: int


class ChunkResponse(BaseModel):
    source_url: str
    output_file: str | None = None
    summary: ChunkingSummaryModel


@router.post("", response_model=ChunkResponse)
async def chunk(request: ChunkRequest) -> ChunkResponse:
    input_path = Path(request.input_file) if request.input_file else INPUT_PATH

    if not input_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Crawled data file not found: {input_path}",
        )

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    source_url = payload.get("source_url", "")

    output_path = OUTPUT_PATH if request.save_json else None
    result = await asyncio.to_thread(run_pipeline, input_path, output_path)

    return ChunkResponse(
        source_url=source_url,
        output_file=str(OUTPUT_PATH) if request.save_json else None,
        summary=ChunkingSummaryModel(**asdict(result.summary)),
    )
