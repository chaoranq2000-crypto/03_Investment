"""Tushare Pro client configured for the local investment system."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable

import tushare as ts


ROOT = Path(__file__).resolve().parents[2]
LOCAL_ENV = ROOT / "investment_system" / "config" / ".env.local"
PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "http_proxy",
    "https_proxy",
    "ALL_PROXY",
    "all_proxy",
)


def load_dotenv(path: Path = LOCAL_ENV) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def clear_proxy_env(keys: Iterable[str] = PROXY_ENV_KEYS) -> None:
    for key in keys:
        os.environ.pop(key, None)


def get_tushare_pro(
    token: str | None = None,
    http_url: str | None = None,
    disable_proxy: bool | None = None,
):
    """Return a Tushare Pro client with the project-local bridge settings."""
    load_dotenv()
    should_disable_proxy = (
        disable_proxy if disable_proxy is not None else env_flag("TUSHARE_DISABLE_PROXY", default=False)
    )
    if should_disable_proxy:
        clear_proxy_env()

    token = token or os.environ.get("TUSHARE_TOKEN")
    if not token:
        raise RuntimeError("TUSHARE_TOKEN is not configured.")

    http_url = http_url or os.environ.get("TUSHARE_HTTP_URL")
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
    print(f"proxy_disabled={env_flag('TUSHARE_DISABLE_PROXY', default=False)}")
    if args.ping:
        df = pro.trade_cal(exchange="", start_date="20260101", end_date="20260105")
        print(df.head(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
