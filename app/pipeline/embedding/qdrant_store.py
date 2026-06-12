"""Qdrant access layer for hybrid (dense + sparse) indexing.

Owns the ``QdrantClient`` lifecycle, collection provisioning with named dense
and sparse vectors, and batched, retried, progress-tracked document uploads via
``QdrantVectorStore`` in hybrid mode.
"""

from __future__ import annotations

import logging

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore, RetrievalMode, SparseEmbeddings
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, SparseVectorParams, VectorParams
from tenacity import (
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_exponential,
)
from tqdm import tqdm

from app.pipeline.embedding.config import EmbeddingSettings

logger = logging.getLogger(__name__)


class QdrantService:
    """Manage a Qdrant collection configured for hybrid search."""

    def __init__(
        self,
        settings: EmbeddingSettings,
        dense_embeddings: Embeddings,
        sparse_embeddings: SparseEmbeddings,
        client: QdrantClient | None = None,
    ) -> None:
        self._settings = settings
        self._dense = dense_embeddings
        self._sparse = sparse_embeddings
        self._client = client or self._build_client(settings)

    @staticmethod
    def _build_client(settings: EmbeddingSettings) -> QdrantClient:
        logger.info("Connecting to Qdrant at %s", settings.qdrant_url)
        return QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=int(settings.qdrant_timeout),
        )

    @property
    def client(self) -> QdrantClient:
        return self._client

    def ensure_collection(self, recreate: bool = False) -> bool:
        """Create the collection if missing (or recreate it).

        Returns ``True`` if the collection was (re)created, ``False`` if an
        existing collection was reused.
        """
        name = self._settings.collection_name
        exists = self._client.collection_exists(name)

        if exists and not recreate:
            logger.info("Reusing existing Qdrant collection '%s'", name)
            return False

        if exists and recreate:
            logger.info("Recreating Qdrant collection '%s'", name)
            self._client.delete_collection(name)

        self._client.create_collection(
            collection_name=name,
            vectors_config={
                self._settings.dense_vector_name: VectorParams(
                    size=self._settings.embedding_dim,
                    distance=Distance.COSINE,
                )
            },
            sparse_vectors_config={
                self._settings.sparse_vector_name: SparseVectorParams(
                    index=models.SparseIndexParams(on_disk=False)
                )
            },
        )
        logger.info("Created Qdrant collection '%s'", name)
        return True

    def build_vector_store(self) -> QdrantVectorStore:
        """Return a hybrid-mode ``QdrantVectorStore`` over the collection."""
        return QdrantVectorStore(
            client=self._client,
            collection_name=self._settings.collection_name,
            embedding=self._dense,
            sparse_embedding=self._sparse,
            retrieval_mode=RetrievalMode.HYBRID,
            vector_name=self._settings.dense_vector_name,
            sparse_vector_name=self._settings.sparse_vector_name,
        )

    def upload_documents(
        self,
        vector_store: QdrantVectorStore,
        documents: list[Document],
    ) -> tuple[int, int]:
        """Batch-upload ``documents`` with retry and a progress bar.

        Uses each document's ``chunk_id`` as the point ID so re-indexing is
        idempotent. Returns ``(uploaded_count, batch_count)``.
        """
        batch_size = self._settings.upload_batch_size

        @retry(
            stop=stop_after_attempt(self._settings.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=30),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        def _add_batch(batch: list[Document], ids: list[str]) -> None:
            vector_store.add_documents(documents=batch, ids=ids)

        uploaded = 0
        batches = 0
        total = len(documents)
        with tqdm(total=total, desc="Indexing", unit="doc") as progress:
            for start in range(0, total, batch_size):
                batch = documents[start : start + batch_size]
                ids = [doc.metadata["chunk_id"] for doc in batch]
                _add_batch(batch, ids)
                uploaded += len(batch)
                batches += 1
                progress.update(len(batch))

        logger.info("Uploaded %d documents in %d batches", uploaded, batches)
        return uploaded, batches
