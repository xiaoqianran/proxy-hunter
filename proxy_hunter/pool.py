"""Round-robin proxy pool with failure tracking."""

from __future__ import annotations

import random
import threading
from dataclasses import dataclass, field


@dataclass
class ProxyEntry:
    url: str
    source_id: str
    latency_ms: float | None = None
    https_ok: bool = False
    failures: int = 0
    successes: int = 0

    @property
    def score(self) -> float:
        base = self.latency_ms if self.latency_ms is not None else 500.0
        return base + self.failures * 2000 - self.successes * 50


@dataclass
class ProxyPool:
    entries: list[ProxyEntry]
    max_failures: int = 5
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _cursor: int = 0

    def __len__(self) -> int:
        return len(self.entries)

    def alive(self) -> list[ProxyEntry]:
        return [e for e in self.entries if e.failures < self.max_failures]

    def acquire(self) -> str | None:
        """Pick next healthy proxy URL (round-robin, skip high failure count)."""
        with self._lock:
            alive = self.alive()
            if not alive:
                # reset failures and retry once
                for e in self.entries:
                    e.failures = 0
                alive = self.entries
            if not alive:
                return None

            alive.sort(key=lambda e: e.score)
            pick = alive[self._cursor % len(alive)]
            self._cursor += 1
            return pick.url

    def report(self, url: str, *, success: bool) -> None:
        with self._lock:
            for e in self.entries:
                if e.url == url:
                    if success:
                        e.successes += 1
                        e.failures = max(0, e.failures - 1)
                    else:
                        e.failures += 1
                    return

    def shuffle(self) -> None:
        with self._lock:
            random.shuffle(self.entries)

    def stats(self) -> dict:
        alive = self.alive()
        return {
            "total": len(self.entries),
            "alive": len(alive),
            "sources": len({e.source_id for e in self.entries}),
        }