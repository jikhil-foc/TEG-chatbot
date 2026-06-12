from fastapi import APIRouter

from app.api.routes import chat, chunk, crawl, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(crawl.router, prefix="/crawl", tags=["crawl"])
api_router.include_router(chunk.router, prefix="/chunk", tags=["chunk"])
