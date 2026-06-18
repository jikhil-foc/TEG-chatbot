import asyncio
import json
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.pipelines.ingestion.langchain_page_chunker import INPUT_PATH, OUTPUT_PATH, run_pipeline
from app.models.chunk import ChunkingSummaryModel, ChunkRequest, ChunkResponse

router = APIRouter()


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
