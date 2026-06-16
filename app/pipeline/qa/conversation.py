"""Conversation message types shared across the QA pipeline."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    """A single turn in the chat history."""

    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)
