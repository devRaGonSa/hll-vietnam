"""Small bounded process-local TTL cache for future CRCON-backed services."""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from threading import RLock
from typing import Generic, TypeVar


Key = TypeVar("Key")
Value = TypeVar("Value")
_MISSING = object()


@dataclass(frozen=True, slots=True)
class _Entry(Generic[Value]):
    value: Value
    expires_at: float


class TtlCache(Generic[Key, Value]):
    """Thread-safe TTL cache with lazy expiry and deterministic LRU eviction."""

    def __init__(
        self,
        *,
        max_entries: int,
        ttl_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_entries <= 0:
            raise ValueError("max_entries must be positive.")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive.")
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries: OrderedDict[Key, _Entry[Value]] = OrderedDict()
        self._lock = RLock()

    def get(self, key: Key, default: Value | None = None) -> Value | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return default
            if entry.expires_at <= self._clock():
                del self._entries[key]
                return default
            self._entries.move_to_end(key)
            return entry.value

    def put(self, key: Key, value: Value, *, ttl_seconds: float | None = None) -> None:
        resolved_ttl = self.ttl_seconds if ttl_seconds is None else ttl_seconds
        if resolved_ttl <= 0:
            raise ValueError("ttl_seconds must be positive.")
        with self._lock:
            now = self._clock()
            self._purge_expired(now)
            self._entries[key] = _Entry(value=value, expires_at=now + resolved_ttl)
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def invalidate(self, key: Key) -> bool:
        with self._lock:
            return self._entries.pop(key, _MISSING) is not _MISSING

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        with self._lock:
            self._purge_expired(self._clock())
            return len(self._entries)

    def _purge_expired(self, now: float) -> None:
        expired = [key for key, entry in self._entries.items() if entry.expires_at <= now]
        for key in expired:
            del self._entries[key]
