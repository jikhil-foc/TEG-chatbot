import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.pipeline.embedding.cache import invalidate_retriever
from app.pipeline.ingestion import IngestionConfig, IngestionResult, run_ingestion_pipeline

router = APIRouter()


class IngestRequest(BaseModel):
    url: str | None = Field(default=None, description="Start URL; defaults to WEBSITE_URL")
    max_depth: int = Field(default=2, ge=0, le=5)
    max_pages: int = Field(default=500, ge=1, le=500)
    include_pdf: bool = True
    include_external: bool = False
    recreate: bool = Field(
        default=False,
        description="Drop and recreate the Qdrant collection before indexing",
    )
    save_json: bool = True


@router.post("/ingest", response_model=IngestionResult)
async def ingest(request: IngestRequest) -> IngestionResult:
    config = IngestionConfig(**request.model_dump())

    try:
        result = await asyncio.to_thread(run_ingestion_pipeline, config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    invalidate_retriever()
    return result
