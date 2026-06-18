"""Multi-step pipeline jobs for ingestion and retrieval.

Ingestion covers crawl → language detection → chunking → Qdrant indexing.
Retrieval exposes hybrid dense + sparse search over the indexed collection.
"""
