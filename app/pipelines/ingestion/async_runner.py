"""Event-loop helpers for running crawler coroutines synchronously."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Coroutine
from typing import TypeVar

_T = TypeVar("_T")


def run_async(coro: Coroutine[object, object, _T]) -> _T:
    """Run a coroutine on a fresh event loop that supports subprocesses.

    On Windows, Playwright (used by crawl4ai) needs a ``ProactorEventLoop`` to
    spawn the browser subprocess. uvicorn's ``--reload`` mode runs on a
    ``SelectorEventLoop``, which cannot, so we always create our own loop here.
    Call this from a worker thread (e.g. via ``asyncio.to_thread``) when the
    caller is already inside another event loop.
    """
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        try:
            loop.close()
        finally:
            asyncio.set_event_loop(None)
