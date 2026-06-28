"""Shared filesystem constants for project-aware workflows."""

from __future__ import annotations

from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
PROJECTS_ROOT = WORKSPACE_ROOT / "investment_system" / "research" / "projects"
SCHEMAS_ROOT = WORKSPACE_ROOT / "investment_system" / "research" / "schemas"

__all__ = [
    "PROJECTS_ROOT",
    "SCHEMAS_ROOT",
    "WORKSPACE_ROOT",
]
