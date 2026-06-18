"""Configuration for the hybrid RAG indexing/retrieval pipeline."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config.data_paths import BM25_STATE_PATH, CHUNKED_DATA_PATH


class EmbeddingSettings(BaseSettings):
    """Runtime configuration for dense/sparse indexing and Qdrant access."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_embedding_model: str = "text-embedding-3-large"
    openai_chat_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI chat model for QA, validation, and suggestions",
    )

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

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_timeout: float = 60.0
    collection_name: str = "teg_chunks"
    dense_vector_name: str = "dense"
    sparse_vector_name: str = "sparse"

    upload_batch_size: int = Field(default=64, ge=1)
    max_retries: int = Field(default=5, ge=1)

    bm25_k1: float = 1.5
    bm25_b: float = 0.75

    rerank_relevance_threshold: float = Field(
        default=0.0,
        description=(
            "Minimum top Cohere rerank_score required to answer; below "
            "this the relevance gate routes to the canned fallback answer"
        ),
    )
    rerank_language_boost: float = Field(
        default=0.25,
        ge=0.0,
        description=(
            "Bonus added to rerank_score when chunk content language matches "
            "the detected query language (English or Irish)"
        ),
    )
    qa_max_validation_retries: int = Field(
        default=2,
        ge=0,
        description="Max answer regenerations when the validation agent fails",
    )

    input_path: Path = CHUNKED_DATA_PATH
    bm25_state_path: Path = BM25_STATE_PATH

    @property
    def token_encoding(self) -> str:
        return "cl100k_base"


@lru_cache(maxsize=1)
def get_embedding_settings() -> EmbeddingSettings:
    return EmbeddingSettings()
