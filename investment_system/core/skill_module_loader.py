"""Load project-local skill modules for shared CLI dispatch."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping

from investment_system.core.constants import WORKSPACE_ROOT


SKILL_SRC_DIRS = [
    WORKSPACE_ROOT / ".codex" / "skills" / "evidence-miner" / "src",
    WORKSPACE_ROOT / ".codex" / "skills" / "quality-auditor" / "src",
    WORKSPACE_ROOT / ".codex" / "skills" / "research-writer" / "src",
    WORKSPACE_ROOT / ".codex" / "skills" / "sector-research-orchestrator" / "src",
    WORKSPACE_ROOT / ".codex" / "skills" / "market-data-router" / "src",
    WORKSPACE_ROOT / ".codex" / "skills" / "financial-data-router" / "src",
    WORKSPACE_ROOT / ".codex" / "skills" / "forecast-normalizer" / "src",
]


def add_skill_src_paths() -> None:
    """Make all project-local skill src roots importable."""
    for path in reversed(SKILL_SRC_DIRS):
        if not path.exists():
            continue
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)


def import_skill_module(module_name: str) -> ModuleType:
    add_skill_src_paths()
    return importlib.import_module(module_name)


def skill_subprocess_env(env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return an environment where project-local skill src roots are importable."""
    result = dict(os.environ if env is None else env)
    skill_paths = [str(path) for path in SKILL_SRC_DIRS if path.exists()]
    existing = result.get("PYTHONPATH", "")
    pythonpath = [*skill_paths]
    if existing:
        pythonpath.append(existing)
    result["PYTHONPATH"] = os.pathsep.join(pythonpath)
    return result


def export_skill_module(module_name: str) -> dict[str, Any]:
    """Return public globals from a skill module."""
    module = import_skill_module(module_name)
    exported = getattr(module, "__all__", None)
    if exported is not None:
        return {name: getattr(module, name) for name in exported}
    return {
        name: value
        for name, value in vars(module).items()
        if not (name.startswith("__") and name.endswith("__"))
    }
