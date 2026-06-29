"""Source-specific request pacing for Tushare calls."""

from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass
from typing import Any

from investment_system.core.data_sources.config import as_float, load_data_source_config


DEFAULT_INTERVAL_SECONDS = 0.7
DEFAULT_JITTER_SECONDS = 0.2


@dataclass(frozen=True)
class RateLimitPolicy:
    interval_seconds: float = DEFAULT_INTERVAL_SECONDS
    jitter_seconds: float = DEFAULT_JITTER_SECONDS

    @classmethod
    def from_env(cls, interval: float | None = None, jitter: float | None = None) -> "RateLimitPolicy":
        config = load_data_source_config()
        tushare = config.section("tushare")
        interval_env = str(tushare.get("request_interval_env") or "TUSHARE_REQUEST_INTERVAL_SECONDS")
        jitter_env = str(tushare.get("request_jitter_env") or "TUSHARE_REQUEST_JITTER_SECONDS")
        default_interval = as_float(tushare.get("rate_limit_seconds"), DEFAULT_INTERVAL_SECONDS)
        default_jitter = as_float(tushare.get("rate_limit_jitter_seconds"), DEFAULT_JITTER_SECONDS)
        raw_interval = os.environ.get(interval_env)
        raw_jitter = os.environ.get(jitter_env)
        return cls(
            interval_seconds=interval if interval is not None else _float_or(raw_interval, default_interval),
            jitter_seconds=jitter if jitter is not None else _float_or(raw_jitter, default_jitter),
        )

    def sleep(self) -> None:
        wait = max(0.0, self.interval_seconds)
        if self.jitter_seconds > 0:
            wait += random.uniform(0.0, self.jitter_seconds)
        if wait:
            time.sleep(wait)


def _float_or(value: Any, default: float) -> float:
    if value is None or not str(value).strip():
        return default
    try:
        return float(value)
    except ValueError:
        return default
