"""Reusable singleton lifecycle management."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import cast

logger = logging.getLogger(__name__)
_UNSET = object()


class SingletonManager[T]:
    """Lazily create one instance and manage its optional async cleanup."""

    def __init__(
        self,
        factory: Callable[[], T],
        aclose: Callable[[T], Awaitable[None]] | None = None,
    ) -> None:
        self._factory = factory
        self._aclose = aclose
        self._instance: T | object = _UNSET
        self._close_tasks: set[asyncio.Task[None]] = set()

    def get(self) -> T:
        """Return the current instance, creating it on first use."""
        if self._instance is _UNSET:
            instance = self._factory()
            self._instance = instance
        return cast(T, self._instance)

    def reset(self) -> None:
        """Drop an instance that does not require asynchronous cleanup."""
        if self._aclose is not None and self._instance is not _UNSET:
            raise RuntimeError("Use aclose() for a singleton with async cleanup")
        self._instance = _UNSET

    def close_in_background(self) -> None:
        """Drop the instance and retain its async close task until completion."""
        if self._instance is _UNSET:
            return
        instance = cast(T, self._instance)
        self._instance = _UNSET
        if self._aclose is None:
            return

        close = self._aclose

        async def close_instance() -> None:
            await close(instance)

        task = asyncio.create_task(close_instance())
        self._close_tasks.add(task)
        task.add_done_callback(self._background_close_done)

    async def aclose(self) -> None:
        """Await cleanup of the current instance and any background closes."""
        if self._instance is not _UNSET:
            instance = cast(T, self._instance)
            if self._aclose is not None:
                await self._aclose(instance)
            self._instance = _UNSET

        if self._close_tasks:
            tasks = tuple(self._close_tasks)
            await asyncio.gather(*tasks)

    def _background_close_done(self, task: asyncio.Task[None]) -> None:
        self._close_tasks.discard(task)
        try:
            task.result()
        except asyncio.CancelledError:
            logger.warning("Background singleton close was cancelled")
        except Exception:
            logger.exception("Background singleton close failed")
