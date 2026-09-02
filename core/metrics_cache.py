"""Bounded, dependency-free cache primitives for expensive DataSense calculations."""
from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from typing import Any, Callable, Hashable


@dataclass(frozen=True)
class CacheStats:
    hits: int
    misses: int
    evictions: int
    size: int


class LRUCache:
    """Thread-safe bounded LRU cache with optional TTL."""

    def __init__(self, maxsize: int = 128, ttl_seconds: float | None = None) -> None:
        if maxsize < 1:
            raise ValueError("maxsize must be positive")
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._items: OrderedDict[Hashable, tuple[float, Any]] = OrderedDict()
        self._hits = self._misses = self._evictions = 0
        self._lock = RLock()

    def get(self, key: Hashable, default: Any = None) -> Any:
        with self._lock:
            item = self._items.get(key)
            if item is None:
                self._misses += 1
                return default
            created, value = item
            if self.ttl_seconds is not None and time.monotonic() - created > self.ttl_seconds:
                self._items.pop(key, None)
                self._misses += 1
                return default
            self._items.move_to_end(key)
            self._hits += 1
            return value

    def set(self, key: Hashable, value: Any) -> None:
        with self._lock:
            self._items[key] = (time.monotonic(), value)
            self._items.move_to_end(key)
            while len(self._items) > self.maxsize:
                self._items.popitem(last=False)
                self._evictions += 1

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def stats(self) -> CacheStats:
        with self._lock:
            return CacheStats(self._hits, self._misses, self._evictions, len(self._items))


def frame_fingerprint(df, columns: list[str] | None = None) -> str:
    """Hash schema/shape/dtypes and pandas row hashes without retaining a copy of the frame."""
    import pandas as pd

    if df is None:
        return "none"
    selected = list(columns or df.columns)
    view = df[selected]
    row_hash = pd.util.hash_pandas_object(view, index=True).to_numpy().tobytes()
    payload = {
        "shape": [int(view.shape[0]), int(view.shape[1])],
        "columns": [(str(c), str(view[c].dtype)) for c in selected],
    }
    digest = hashlib.sha256()
    digest.update(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode())
    digest.update(row_hash)
    return digest.hexdigest()


def cached_call(cache: LRUCache, key: Hashable, fn: Callable[[], Any]) -> Any:
    value = cache.get(key, default=None)
    if value is not None:
        return value
    value = fn()
    cache.set(key, value)
    return value
