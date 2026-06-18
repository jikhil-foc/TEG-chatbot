"""Dense embedding service backed by OpenAI ``text-embedding-3-large``.

Wraps :class:`langchain_openai.OpenAIEmbeddings` with explicit configuration and
built-in retry on transient API failures. The returned object satisfies the
LangChain ``Embeddings`` interface and can be passed directly to
``QdrantVectorStore``.
"""

from __future__ import annotations

import logging

from langchain_openai import OpenAIEmbeddings

from app.config.embedding_settings import EmbeddingSettings

logger = logging.getLogger(__name__)


def build_dense_embeddings(settings: EmbeddingSettings) -> OpenAIEmbeddings:
    """Construct an ``OpenAIEmbeddings`` client from ``settings``.

    Retries are delegated to the underlying OpenAI client via ``max_retries``,
    which applies exponential backoff to rate-limit and transient errors.
    """
    if not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY is not set. Add it to your environment or .env file."
        )

    logger.info(
        "Initialising dense embeddings: model=%s dim=%d",
        settings.openai_embedding_model,
        settings.embedding_dim,
    )
    return OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        api_key=settings.openai_api_key,
        dimensions=settings.embedding_dim,
        chunk_size=settings.embedding_batch_size,
        max_retries=settings.max_retries,
        timeout=settings.qdrant_timeout,
    )
