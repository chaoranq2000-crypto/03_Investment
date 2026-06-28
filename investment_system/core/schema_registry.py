"""Shared schema registry facade for project-aware workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from investment_system.core.constants import SCHEMAS_ROOT
from investment_system.core.output_contracts import get_output_schema

__all__ = [
    "SCHEMAS_ROOT",
    "get_nested",
    "get_output_schema",
    "load_schema",
    "load_yaml",
]


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file into a dict, returning an empty dict when absent."""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_nested(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Read nested dict keys without raising on missing intermediate values."""
    for key in keys:
        if not isinstance(data, dict):
            return default
        data = data.get(key, default)
    return data


def load_schema(name: str) -> dict[str, Any]:
    """Load a schema file from `investment_system/research/schemas`."""
    path = Path(name)
    if not path.suffix:
        path = path.with_suffix(".yaml")
    if not path.is_absolute():
        path = SCHEMAS_ROOT / path
    return load_yaml(path)
