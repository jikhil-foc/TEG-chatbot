"""In-memory session store for multi-turn clarification state."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

_SESSION_TTL_SECONDS = 60 * 30


@dataclass
class PendingClarification:
    """Slots collected before the user question is specific enough to retrieve."""

    partial_query: str
    intent: str = ""
    missing_slots: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


_lock = threading.Lock()
_sessions: dict[str, PendingClarification] = {}


def _purge_expired(now: float | None = None) -> None:
    now = now or time.time()
    expired = [
        session_id
        for session_id, pending in _sessions.items()
        if now - pending.created_at > _SESSION_TTL_SECONDS
    ]
    for session_id in expired:
        _sessions.pop(session_id, None)


def get_pending(session_id: str | None) -> PendingClarification | None:
    if not session_id:
        return None

    with _lock:
        _purge_expired()
        return _sessions.get(session_id)


def set_pending(session_id: str, pending: PendingClarification) -> None:
    with _lock:
        _purge_expired()
        _sessions[session_id] = pending


def clear_pending(session_id: str | None) -> None:
    if not session_id:
        return

    with _lock:
        _sessions.pop(session_id, None)


def reset_sessions() -> None:
    with _lock:
        _sessions.clear()
