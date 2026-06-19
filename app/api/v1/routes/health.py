from fastapi import APIRouter

from app.db.content_registry_repository import get_content_registry_counts
from app.db.database_session import session_scope

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, object]:
    """Report API status and content-registry row counts from the active database."""
    try:
        with session_scope() as session:
            registry = get_content_registry_counts(session)
        return {
            "status": "ok",
            "database": "connected",
            "registry": registry,
        }
    except Exception as exc:
        return {
            "status": "degraded",
            "database": "unavailable",
            "error": str(exc),
        }
