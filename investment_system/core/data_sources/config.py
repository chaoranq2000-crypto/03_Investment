"""Runtime configuration loader for shared data-source facades.

This module owns local provider/runtime configuration only. Skill-owned
endpoint registries stay under `.codex/skills/*`.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from investment_system.core.constants import WORKSPACE_ROOT


CONFIG_ENV = "INVESTMENT_SYSTEM_CONFIG"
CONFIG_DIR = WORKSPACE_ROOT / "investment_system" / "config"
DEFAULT_CONFIG = CONFIG_DIR / "data_sources.example.toml"
LOCAL_CONFIG = CONFIG_DIR / "data_sources.local.toml"
LOCAL_ENV = CONFIG_DIR / ".env.local"

__all__ = [
    "CONFIG_DIR",
    "CONFIG_ENV",
    "DEFAULT_CONFIG",
    "LOCAL_CONFIG",
    "LOCAL_ENV",
    "DataSourceConfig",
    "as_bool",
    "as_float",
    "load_data_source_config",
    "load_dotenv",
    "resolve_config_path",
    "workspace_path",
]


@dataclass(frozen=True)
class DataSourceConfig:
    path: Path
    raw: dict[str, Any]

    def section(self, name: str) -> dict[str, Any]:
        value = self.raw.get(name, {})
        return value if isinstance(value, dict) else {}


def workspace_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return WORKSPACE_ROOT / path


def load_dotenv(path: Path = LOCAL_ENV) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def resolve_config_path() -> Path:
    override = os.environ.get(CONFIG_ENV, "").strip()
    if override:
        return workspace_path(override)
    if LOCAL_CONFIG.exists():
        return LOCAL_CONFIG
    return DEFAULT_CONFIG


def load_data_source_config(load_env: bool = True) -> DataSourceConfig:
    if load_env:
        load_dotenv()
    path = resolve_config_path()
    if not path.exists():
        return DataSourceConfig(path=path, raw={})
    return DataSourceConfig(path=path, raw=tomllib.loads(path.read_text(encoding="utf-8")))


def as_float(value: Any, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
