"""Rate limiting and retry helpers for public data sources.

These helpers intentionally favor slow, cache-friendly research ingestion over
fast scraping. Public web-backed providers such as AKShare should be queried as
low-frequency batch sources, not as realtime loops.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class HumanRateLimiter:
    """Sleep between calls with jitter so requests do not look like a tight loop."""

    min_interval_seconds: float = 8.0
    jitter_seconds: float = 4.0
    _last_call: float = field(default=0.0, init=False)

    def wait(self) -> float:
        now = time.monotonic()
        elapsed = now - self._last_call if self._last_call else None
        target = self.min_interval_seconds + random.uniform(0, self.jitter_seconds)
        sleep_for = target if elapsed is None else max(0.0, target - elapsed)
        if sleep_for > 0:
            time.sleep(sleep_for)
        self._last_call = time.monotonic()
        return sleep_for


def call_with_retries(
    label: str,
    func: Callable[[], Any],
    *,
    limiter: HumanRateLimiter,
    retries: int = 2,
    retry_backoff_seconds: float = 20.0,
) -> dict[str, Any]:
    """Call a provider function slowly and return structured success/error data."""

    attempts: list[dict[str, Any]] = []
    for attempt_no in range(1, retries + 2):
        slept = limiter.wait()
        try:
            data = func()
            return {
                "label": label,
                "ok": True,
                "attempt": attempt_no,
                "slept_before_call_seconds": round(slept, 3),
                "data": data,
            }
        except Exception as exc:  # provider libraries raise mixed exception types
            attempts.append(
                {
                    "attempt": attempt_no,
                    "slept_before_call_seconds": round(slept, 3),
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )
            if attempt_no <= retries:
                backoff = retry_backoff_seconds * attempt_no + random.uniform(0, 5)
                attempts[-1]["retry_backoff_after_seconds"] = round(backoff, 3)
                time.sleep(backoff)
    return {"label": label, "ok": False, "attempts": attempts}
