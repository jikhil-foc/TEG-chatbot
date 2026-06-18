"""Tests for Qdrant point deletion helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.config.embedding_settings import EmbeddingSettings
from app.services.qdrant_vector_store import QdrantService


def test_delete_points_by_chunk_ids_calls_client_delete() -> None:
    settings = EmbeddingSettings(openai_api_key="test-key")
    client = MagicMock()
    service = QdrantService(
        settings=settings,
        dense_embeddings=MagicMock(),
        sparse_embeddings=MagicMock(),
        client=client,
    )

    deleted = service.delete_points_by_chunk_ids(["chunk-a", "chunk-b"])

    assert deleted == 2
    client.delete.assert_called_once()


def test_delete_points_by_section_id_calls_filter_delete() -> None:
    settings = EmbeddingSettings(openai_api_key="test-key")
    client = MagicMock()
    service = QdrantService(
        settings=settings,
        dense_embeddings=MagicMock(),
        sparse_embeddings=MagicMock(),
        client=client,
    )

    service.delete_points_by_section_id("section-123")

    client.delete.assert_called_once()
