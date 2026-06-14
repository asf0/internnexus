"""Unit tests for pipeline.utils.lru.LRUDict."""

from __future__ import annotations

import pytest

from pipeline.utils.lru import LRUDict


def test_lru_evicts_oldest_on_insertion() -> None:
    cache = LRUDict[str, int](max_size=2)
    cache["a"] = 1
    cache["b"] = 2
    cache["c"] = 3

    assert "a" not in cache
    assert "b" in cache
    assert "c" in cache


def test_lru_access_moves_item_to_end() -> None:
    cache = LRUDict[str, int](max_size=2)
    cache["a"] = 1
    cache["b"] = 2
    _ = cache["a"]  # access a
    cache["c"] = 3

    assert "a" in cache
    assert "b" not in cache
    assert "c" in cache


def test_lru_update_maintains_order() -> None:
    cache = LRUDict[str, int](max_size=2)
    cache["a"] = 1
    cache["b"] = 2
    cache["a"] = 10  # update a -> moves to end
    cache["c"] = 3

    assert "a" in cache
    assert "b" not in cache
    assert "c" in cache
    assert cache["a"] == 10


def test_lru_get_updates_access_order() -> None:
    cache = LRUDict[str, int](max_size=2)
    cache["a"] = 1
    cache["b"] = 2
    assert cache.get("a") == 1
    cache["c"] = 3
    assert "a" in cache
    assert "b" not in cache


def test_lru_get_missing_returns_default() -> None:
    cache = LRUDict[str, int](max_size=2)
    assert cache.get("missing") is None
    assert cache.get("missing", 42) == 42


def test_lru_rejects_invalid_size() -> None:
    with pytest.raises(ValueError):
        LRUDict[str, int](max_size=0)
