"""Check unified investment data-source configuration without network calls."""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "investment_system" / "config" / "data_sources.example.toml"
LOCAL_CONFIG = ROOT / "investment_system" / "config" / "data_sources.local.toml"
LOCAL_ENV = ROOT / "investment_system" / "config" / ".env.local"


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def load_legacy_key_value_file(path: Path, keys: list[str]) -> None:
    if not path.exists():
        return
    wanted = set(keys)
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in wanted:
            os.environ.setdefault(key, value.strip())


def has_module(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


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


def main() -> int:
    load_dotenv(LOCAL_ENV)

    config_path = LOCAL_CONFIG if LOCAL_CONFIG.exists() else CONFIG
    if not config_path.exists():
        print(status("config", False, str(config_path)))
        return 1

    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    print(status("config", True, str(config_path)))
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

    guosen = config.get("guosen", {})
    if guosen.get("enabled", False):
        token_env = guosen.get("token_env", "GS_API_KEY")
        print(status(f"{token_env} env", bool(os.environ.get(token_env))))
        backup_env = guosen.get("backup_token_env", "")
        if backup_env:
            print(status(f"{backup_env} env", bool(os.environ.get(backup_env))))
        print(status("Guosen python path", Path(guosen.get("python", "")).exists(), guosen.get("python", "")))
        print(status("Guosen local adapter", Path(guosen.get("local_adapter", "")).exists(), guosen.get("local_adapter", "")))
    else:
        print(status("Guosen", True, "disabled"))

    print()

    baostock = config.get("baostock", {})
    if baostock.get("enabled", False):
        baostock_python = baostock.get("python", "")
        baostock_module = baostock.get("module_check", "baostock")
        print(status("BaoStock python path", Path(baostock_python).exists(), baostock_python))
        print(status("BaoStock module in configured python", python_has_module(baostock_python, baostock_module)))
    else:
        print(status("BaoStock", True, "disabled"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
