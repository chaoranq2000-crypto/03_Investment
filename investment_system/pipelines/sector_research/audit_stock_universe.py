"""Compatibility wrapper for quality_auditor.stock_universe.

Business logic has moved to ``quality_auditor.stock_universe``. Keep this module for legacy
``python -m investment_system.pipelines`` callers.
"""

from __future__ import annotations

from investment_system.core.skill_module_loader import export_skill_module

globals().update(export_skill_module("quality_auditor.stock_universe"))

if __name__ == "__main__":
    _main = globals().get("main")
    if _main is None:
        raise SystemExit("No CLI main is defined for quality_auditor.stock_universe.")
    raise SystemExit(_main())
