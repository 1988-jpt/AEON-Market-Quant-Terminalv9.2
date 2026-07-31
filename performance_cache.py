"""Caché TTL thread-safe, pequeña y sin dependencias externas."""
from __future__ import annotations

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable, Generic, Hashable, Optional, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


@dataclass
class _Entry(Generic[V]):
    value: V
    expires_at: float


class TTLCache(Generic[K, V]):
    def __init__(self, ttl_seconds: float = 5.0, max_items: int = 128, clock: Callable[[], float] = time.monotonic):
        if ttl_seconds <= 0 or max_items <= 0:
            raise ValueError("ttl_seconds y max_items deben ser positivos")
        self.ttl_seconds = float(ttl_seconds)
        self.max_items = int(max_items)
        self._clock = clock
        self._data: OrderedDict[K, _Entry[V]] = OrderedDict()
        self._lock = threading.RLock()
        self.hits = 0
        self.misses = 0

    def get(self, key: K) -> Optional[V]:
        with self._lock:
            entry = self._data.get(key)
            now = self._clock()
            if entry is None or entry.expires_at <= now:
                if entry is not None:
                    self._data.pop(key, None)
                self.misses += 1
                return None
            self._data.move_to_end(key)
            self.hits += 1
            return entry.value

    def set(self, key: K, value: V, ttl_seconds: Optional[float] = None) -> None:
        ttl = self.ttl_seconds if ttl_seconds is None else float(ttl_seconds)
        if ttl <= 0:
            raise ValueError("ttl_seconds debe ser positivo")
        with self._lock:
            self._data[key] = _Entry(value=value, expires_at=self._clock() + ttl)
            self._data.move_to_end(key)
            while len(self._data) > self.max_items:
                self._data.popitem(last=False)

    def get_or_compute(self, key: K, factory: Callable[[], V], ttl_seconds: Optional[float] = None) -> V:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = factory()
        self.set(key, value, ttl_seconds)
        return value

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0
