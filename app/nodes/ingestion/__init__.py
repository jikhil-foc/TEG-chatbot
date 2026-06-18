"""Ingestion graph nodes.

Linear pipeline: crawl → detect language → chunk → embed to Qdrant.
"""

from app.nodes.ingestion.chunk_crawled_pages import chunk_node
from app.nodes.ingestion.crawl_teg_website import crawl_node
from app.nodes.ingestion.enrich_page_languages import detect_language_node
from app.nodes.ingestion.index_chunks_in_qdrant import embed_to_qdrant_node

__all__ = [
    "chunk_node",
    "crawl_node",
    "detect_language_node",
    "embed_to_qdrant_node",
]
