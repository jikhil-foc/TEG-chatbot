import asyncio

from fastapi import APIRouter, HTTPException

from app.models.ingest_request import IngestionConfig, IngestionResult
from app.models.ingestion import IngestRequest
from app.application import teg_ingest_facade as ingestion_service

router = APIRouter()


@router.post("/ingest", response_model=IngestionResult)
async def ingest(request: IngestRequest) -> IngestionResult:
    config = IngestionConfig(**request.model_dump())

    try:
        return await asyncio.to_thread(ingestion_service.ingest, config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
