"""Compatibility wrapper for research_writer.output_writers.

Business logic has moved to ``research_writer.output_writers``. Keep this module for legacy
``python -m investment_system.pipelines`` callers.
"""

from __future__ import annotations

from investment_system.core.skill_module_loader import export_skill_module

globals().update(export_skill_module("research_writer.output_writers"))

if __name__ == "__main__":
    _main = globals().get("main")
    if _main is None:
        raise SystemExit("No CLI main is defined for research_writer.output_writers.")
    raise SystemExit(_main())
