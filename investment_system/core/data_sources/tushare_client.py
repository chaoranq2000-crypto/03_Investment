"""Tushare Pro client configured for the local investment system."""

from __future__ import annotations

import argparse
import os
from typing import Iterable

import tushare as ts

from investment_system.core.constants import WORKSPACE_ROOT
from investment_system.core.data_sources.config import (
    LOCAL_ENV,
    as_bool,
    load_data_source_config,
    load_dotenv,
)


ROOT = WORKSPACE_ROOT
PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "http_proxy",
    "https_proxy",
    "ALL_PROXY",
    "all_proxy",
)

__all__ = [
    "LOCAL_ENV",
    "PROXY_ENV_KEYS",
    "ROOT",
    "clear_proxy_env",
    "env_flag",
    "get_tushare_pro",
    "load_dotenv",
]


def env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def clear_proxy_env(keys: Iterable[str] = PROXY_ENV_KEYS) -> None:
    for key in keys:
        os.environ.pop(key, None)


def _env_name(section: dict, key: str, default: str) -> str:
    return str(section.get(key) or default)


def get_tushare_pro(
    token: str | None = None,
    http_url: str | None = None,
    disable_proxy: bool | None = None,
):
    """Return a Tushare Pro client with the project-local bridge settings."""
    config = load_data_source_config()
    tushare = config.section("tushare")
    token_env = _env_name(tushare, "token_env", "TUSHARE_TOKEN")
    http_url_env = _env_name(tushare, "http_url_env", "TUSHARE_HTTP_URL")
    disable_proxy_env = _env_name(tushare, "disable_proxy_env", "TUSHARE_DISABLE_PROXY")
    disable_proxy_default = as_bool(tushare.get("disable_proxy_default"), False)
    should_disable_proxy = (
        disable_proxy
        if disable_proxy is not None
        else env_flag(disable_proxy_env, default=disable_proxy_default)
    )
    if should_disable_proxy:
        clear_proxy_env()

    token = token or os.environ.get(token_env)
    if not token:
        raise RuntimeError(f"{token_env} is not configured.")

    http_url = http_url or os.environ.get(http_url_env)
    pro = ts.pro_api(token)
    if http_url:
        pro._DataApi__http_url = http_url
    return pro


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ping", action="store_true", help="Run a tiny trade calendar request.")
    args = parser.parse_args()

    pro = get_tushare_pro()
    print(f"tushare_version={getattr(ts, '__version__', 'unknown')}")
    print(f"http_url={getattr(pro, '_DataApi__http_url', '')}")
    tushare = load_data_source_config().section("tushare")
    disable_proxy_env = _env_name(tushare, "disable_proxy_env", "TUSHARE_DISABLE_PROXY")
    disable_proxy_default = as_bool(tushare.get("disable_proxy_default"), False)
    print(f"proxy_disabled={env_flag(disable_proxy_env, default=disable_proxy_default)}")
    if args.ping:
        try:
            df = pro.trade_cal(exchange="", start_date="20260101", end_date="20260105")
        except Exception as exc:
            print("tushare_ping_status=failed")
            print(f"error={type(exc).__name__}: {exc}")
            return 1
        print("tushare_ping_status=ok")
        print(df.head(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
