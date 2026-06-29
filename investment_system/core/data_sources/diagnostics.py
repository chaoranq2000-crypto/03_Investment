"""Check investment data-source runtime configuration without network calls."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from investment_system.core.data_sources.config import (
    CONFIG_ENV,
    LOCAL_ENV,
    as_float,
    load_data_source_config,
)


def python_has_module(python_path: str, module_name: str) -> bool:
    path = Path(python_path)
    if not path.exists():
        return False
    result = subprocess.run(
        [str(path), "-c", f"import {module_name}"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def status(label: str, ok: bool, detail: str = "") -> str:
    mark = "OK" if ok else "MISSING"
    suffix = f" - {detail}" if detail else ""
    return f"[{mark}] {label}{suffix}"


def env_name(section: dict, key: str, default: str) -> str:
    return str(section.get(key) or default)


def main() -> int:
    loaded = load_data_source_config()
    config_path = loaded.path
    if not config_path.exists():
        print(status("config", False, str(config_path)))
        return 1

    config = loaded.raw
    print(status("config", True, str(config_path)))
    if os.environ.get(CONFIG_ENV):
        print(status(CONFIG_ENV, True, os.environ[CONFIG_ENV]))
    print(status(".env.local", LOCAL_ENV.exists(), str(LOCAL_ENV)))
    print()

    akshare = config.get("akshare", {})
    if akshare.get("enabled", False):
        akshare_python = akshare.get("python", "")
        akshare_module = akshare.get("module_check", "akshare")
        print(status("AKShare python path", Path(akshare_python).exists(), akshare_python))
        print(status("AKShare module in configured python", python_has_module(akshare_python, akshare_module)))
    else:
        print(status("AKShare", True, "disabled"))

    print()

    baostock = config.get("baostock", {})
    if baostock.get("enabled", False):
        baostock_python = baostock.get("python", "")
        baostock_module = baostock.get("module_check", "baostock")
        print(status("BaoStock python path", Path(baostock_python).exists(), baostock_python))
        print(status("BaoStock module in configured python", python_has_module(baostock_python, baostock_module)))
    else:
        print(status("BaoStock", True, "disabled"))

    print()

    tushare = config.get("tushare", {})
    if tushare.get("enabled", False):
        token_env = env_name(tushare, "token_env", "TUSHARE_TOKEN")
        http_url_env = env_name(tushare, "http_url_env", "TUSHARE_HTTP_URL")
        disable_proxy_env = env_name(tushare, "disable_proxy_env", "TUSHARE_DISABLE_PROXY")
        interval_env = env_name(tushare, "request_interval_env", "TUSHARE_REQUEST_INTERVAL_SECONDS")
        jitter_env = env_name(tushare, "request_jitter_env", "TUSHARE_REQUEST_JITTER_SECONDS")
        tushare_python = tushare.get("python", "")
        tushare_module = tushare.get("module_check", "tushare")
        default_interval = as_float(tushare.get("rate_limit_seconds"), 0.7)
        default_jitter = as_float(tushare.get("rate_limit_jitter_seconds"), 0.2)
        print(status(f"{token_env} env", bool(os.environ.get(token_env))))
        print(status(f"{http_url_env} env", bool(os.environ.get(http_url_env)), os.environ.get(http_url_env, "")))
        print(status(f"{disable_proxy_env} env", bool(os.environ.get(disable_proxy_env)), os.environ.get(disable_proxy_env, "")))
        print(status(f"{interval_env} env/default", True, os.environ.get(interval_env, str(default_interval))))
        print(status(f"{jitter_env} env/default", True, os.environ.get(jitter_env, str(default_jitter))))
        print(status("Tushare python path", Path(tushare_python).exists(), tushare_python))
        print(status("Tushare module in configured python", python_has_module(tushare_python, tushare_module)))
    else:
        print(status("Tushare", True, "disabled"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
