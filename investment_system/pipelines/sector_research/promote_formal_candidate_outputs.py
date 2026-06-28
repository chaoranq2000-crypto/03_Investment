"""Compatibility wrapper for sector_research_orchestrator.promote.

Business logic has moved to ``sector_research_orchestrator.promote``. Keep this module for legacy
``python -m investment_system.pipelines`` callers.
"""

from __future__ import annotations

from investment_system.core.skill_module_loader import export_skill_module

globals().update(export_skill_module("sector_research_orchestrator.promote"))

if __name__ == "__main__":
    _main = globals().get("main")
    if _main is None:
        raise SystemExit("No CLI main is defined for sector_research_orchestrator.promote.")
    raise SystemExit(_main())
