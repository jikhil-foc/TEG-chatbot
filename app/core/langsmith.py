"""LangSmith tracing configuration for LangChain and LangGraph runs."""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_CONFIGURED = False


class LangSmithSettings(BaseSettings):
    """LangSmith observability settings loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    langsmith_tracing: bool = Field(
        default=False,
        description="Enable LangSmith tracing for LangChain/LangGraph runs",
    )
    langsmith_api_key: str | None = Field(
        default=None,
        description="LangSmith API key (lsv2_...)",
    )
    langsmith_project: str = Field(
        default="teg-chatbot",
        description="LangSmith project name for traces",
    )
    langsmith_endpoint: str | None = Field(
        default=None,
        description="LangSmith API URL (required for EU region accounts)",
    )


@lru_cache(maxsize=1)
def get_langsmith_settings() -> LangSmithSettings:
    """Return cached LangSmith settings."""
    return LangSmithSettings()


def configure_langsmith() -> bool:
    """Apply LangSmith environment variables for automatic tracing.

    LangChain chat/embedding calls and LangGraph ``invoke`` runs are traced
    when tracing is enabled and an API key is present. Safe to call multiple
    times; configuration is applied only once per process.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return os.environ.get("LANGSMITH_TRACING", "").lower() == "true"

    settings = get_langsmith_settings()
    _CONFIGURED = True

    if not settings.langsmith_tracing:
        logger.debug("LangSmith tracing is disabled")
        return False

    if not settings.langsmith_api_key:
        logger.warning(
            "LANGSMITH_TRACING is enabled but LANGSMITH_API_KEY is not set; "
            "traces will not be sent to LangSmith"
        )
        return False

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    if settings.langsmith_endpoint:
        os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint

    # Legacy env names still read by some LangChain integrations.
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project

    logger.info("LangSmith tracing enabled (project=%r)", settings.langsmith_project)
    return True


def is_langsmith_enabled() -> bool:
    """Return whether LangSmith tracing is active in this process."""
    return configure_langsmith()


def build_run_config(
    *,
    run_name: str,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a RunnableConfig dict for ``graph.invoke`` trace context."""
    config: dict[str, Any] = {"run_name": run_name}
    if tags:
        config["tags"] = tags
    if metadata:
        config["metadata"] = metadata
    return config
