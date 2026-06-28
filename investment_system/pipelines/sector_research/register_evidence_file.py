"""Compatibility wrapper for evidence_miner.register.

Business logic has moved to ``evidence_miner.register``. Keep this module for legacy
``python -m investment_system.pipelines`` callers.
"""

from __future__ import annotations

from investment_system.core.skill_module_loader import export_skill_module

globals().update(export_skill_module("evidence_miner.register"))

if __name__ == "__main__":
    _main = globals().get("main")
    if _main is None:
        raise SystemExit("No CLI main is defined for evidence_miner.register.")
    raise SystemExit(_main())
