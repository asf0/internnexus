"""Small, reusable LRU cache backed by OrderedDict."""

from __future__ import annotations

from collections import OrderedDict
from typing import Generic, TypeVar

KT = TypeVar("KT")
VT = TypeVar("VT")


class LRUDict(Generic[KT, VT]):
    """A dictionary with a bounded size and LRU eviction on insertion/access.

    The least-recently *accessed* item is evicted when the size exceeds
    ``max_size``. Reads, writes, and the ``get`` method all count as access.
    """

    def __init__(self, max_size: int) -> None:
        if max_size < 1:
            raise ValueError("max_size must be at least 1")
        self.max_size = max_size
        self._data: OrderedDict[KT, VT] = OrderedDict()

    def __contains__(self, key: object) -> bool:
        return key in self._data

    def __getitem__(self, key: KT) -> VT:
        self._data.move_to_end(key)
        return self._data[key]

    def __setitem__(self, key: KT, value: VT) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        while len(self._data) > self.max_size:
            self._data.popitem(last=False)

    def __len__(self) -> int:
        return len(self._data)

    def get(self, key: KT, default: VT | None = None) -> VT | None:
        if key in self._data:
            self._data.move_to_end(key)
            return self._data[key]
        return default

    def items(self):
        return self._data.items()

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()
