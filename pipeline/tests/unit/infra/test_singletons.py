"""Tests for shared singleton lifecycle management."""

from __future__ import annotations

import asyncio

import pytest

from pipeline.infra.singletons import SingletonManager


def test_get_reuses_instance_and_reset_recreates() -> None:
    created: list[object] = []

    def factory() -> object:
        instance = object()
        created.append(instance)
        return instance

    manager = SingletonManager(factory)

    assert manager.get() is manager.get()
    manager.reset()
    assert manager.get() is not created[0]
    assert len(created) == 2


def test_failed_factory_is_not_cached() -> None:
    attempts = 0

    def factory() -> object:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("not configured")
        return object()

    manager = SingletonManager(factory)

    with pytest.raises(RuntimeError, match="not configured"):
        manager.get()
    assert manager.get() is manager.get()
    assert attempts == 2


@pytest.mark.asyncio
async def test_aclose_closes_and_drops_instance() -> None:
    created: list[object] = []
    closed: list[object] = []

    def factory() -> object:
        instance = object()
        created.append(instance)
        return instance

    async def close(instance: object) -> None:
        closed.append(instance)

    manager = SingletonManager(factory, aclose=close)
    first = manager.get()

    await manager.aclose()

    assert closed == [first]
    assert manager.get() is not first


@pytest.mark.asyncio
async def test_background_close_is_retained_and_awaited() -> None:
    close_started = asyncio.Event()
    allow_close = asyncio.Event()
    closed: list[object] = []

    async def close(instance: object) -> None:
        close_started.set()
        await allow_close.wait()
        closed.append(instance)

    manager = SingletonManager(object, aclose=close)
    first = manager.get()
    manager.close_in_background()
    await close_started.wait()

    waiter = asyncio.create_task(manager.aclose())
    await asyncio.sleep(0)
    assert not waiter.done()

    allow_close.set()
    await waiter
    assert closed == [first]


def test_reset_rejects_live_instance_with_async_cleanup() -> None:
    async def close(_instance: object) -> None:
        return None

    manager = SingletonManager(object, aclose=close)
    manager.get()

    with pytest.raises(RuntimeError, match=r"Use aclose\(\)"):
        manager.reset()
