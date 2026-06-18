import asyncio

from fastapi import APIRouter, HTTPException

from app.db.database_session import session_scope
from app.models.ingest_request import ContentChangeStepSummary, IngestionConfig, IngestionResult
from app.models.ingestion import IngestRequest
from app.application import teg_ingest_facade as ingestion_service
from app.pipelines.ingestion.langchain_page_chunker import load
from app.pipelines.ingestion.content_change_detector import detect_content_changes
from app.pipelines.ingestion.sync_changed_sections_job import sync_changed_sections_to_qdrant
from app.pipelines.retrieval.retriever_cache import invalidate_retriever

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


@router.post("/sync", response_model=ContentChangeStepSummary)
async def sync_content_registry() -> ContentChangeStepSummary:
    """Detect changes from the latest crawled JSON and sync Qdrant."""
    from app.config.data_paths import CRAWLED_DATA_PATH

    try:
        pages = load(CRAWLED_DATA_PATH)
        with session_scope() as session:
            change_report = detect_content_changes(pages, session)
        result = await asyncio.to_thread(sync_changed_sections_to_qdrant, change_report)
        invalidate_retriever()
        return ContentChangeStepSummary(
            unchanged_sections=result["change_unchanged_sections"],
            changed_sections=result["change_changed_sections"],
            removed_sections=result["change_removed_sections"],
            removed_chunks=result["change_removed_chunks"],
            changed_chunks=result["change_changed_chunks"],
            dense_embeddings_generated=result["index_dense_embeddings_generated"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
