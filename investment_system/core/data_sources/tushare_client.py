"""Stable Tushare client facade for skill modules."""

from __future__ import annotations

from investment_system.pipelines.tushare_client import (
    LOCAL_ENV,
    PROXY_ENV_KEYS,
    ROOT,
    clear_proxy_env,
    env_flag,
    get_tushare_pro,
    load_dotenv,
)
from investment_system.pipelines.tushare_client import main as _legacy_main

__all__ = [
    "LOCAL_ENV",
    "PROXY_ENV_KEYS",
    "ROOT",
    "clear_proxy_env",
    "env_flag",
    "get_tushare_pro",
    "load_dotenv",
]


def main() -> int:
    """Run the legacy Tushare CLI through the new core facade."""
    return _legacy_main()


if __name__ == "__main__":
    raise SystemExit(main())
