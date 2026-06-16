"""Configuration for the hybrid RAG indexing/retrieval pipeline.

Settings are loaded from the environment (and the project ``.env`` file) via
``pydantic-settings``, mirroring :mod:`app.core.config`. All values have sane
defaults except ``openai_api_key``, which must be supplied by the environment.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.paths import BM25_STATE_PATH, CHUNKED_DATA_PATH


class EmbeddingSettings(BaseSettings):
    """Runtime configuration for dense/sparse indexing and Qdrant access."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenAI dense embeddings.
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_embedding_model: str = "text-embedding-3-large"
    openai_chat_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI chat model for QA, validation, and suggestions",
    )

    # Cohere reranking.
    cohere_api_key: str = Field(default="", description="Cohere API key")
    cohere_rerank_model: str = Field(
        default="rerank-v3.5",
        description="Cohere rerank model name",
    )
    embedding_dim: int = 3072
    embedding_batch_size: int = Field(
        default=128,
        ge=1,
        description="Texts per OpenAI embedding request",
    )

    # Qdrant connection (local by default).
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_timeout: float = 60.0
    collection_name: str = "teg_chunks"
    dense_vector_name: str = "dense"
    sparse_vector_name: str = "sparse"

    # Upload behaviour.
    upload_batch_size: int = Field(default=64, ge=1)
    max_retries: int = Field(default=5, ge=1)

    # BM25 sparse encoder parameters.
    bm25_k1: float = 1.5
    bm25_b: float = 0.75

    # QA pipeline behaviour.
    rerank_relevance_threshold: float = Field(
        default=0.0,
        description=(
            "Minimum top Cohere rerank_score required to answer; below "
            "this the relevance gate routes to the canned fallback answer"
        ),
    )
    qa_max_validation_retries: int = Field(
        default=2,
        ge=0,
        description="Max answer regenerations when the validation agent fails",
    )

    # Filesystem paths.
    input_path: Path = CHUNKED_DATA_PATH
    bm25_state_path: Path = BM25_STATE_PATH

    @property
    def token_encoding(self) -> str:
        """tiktoken encoding name used for token counting (matches the model)."""
        return "cl100k_base"


@lru_cache(maxsize=1)
def get_embedding_settings() -> EmbeddingSettings:
    """Return a cached :class:`EmbeddingSettings` instance."""
    return EmbeddingSettings()
