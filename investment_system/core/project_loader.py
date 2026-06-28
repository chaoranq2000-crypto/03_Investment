"""Stable project-loading facade for skill modules.

The implementation still lives in
`investment_system.pipelines.sector_research.load_project` during Phase 1.
Keep this module small until the old loader is split into true core modules.
"""

from __future__ import annotations

from investment_system.core.constants import PROJECTS_ROOT, SCHEMAS_ROOT, WORKSPACE_ROOT
from investment_system.core.audit_types import ValidationWarning
from investment_system.core.evidence_registry import (
    build_legacy_sector_map,
    get_sector,
    get_stocks_for_sector,
    list_scoring_sectors,
    resolve_evidence_files_for_sector,
    resolve_sector_id,
)
from investment_system.core.path_resolver import safe_filename
from investment_system.core.output_contracts import (
    get_output_contract,
    get_output_schema,
    get_output_spec,
    list_output_types,
    resolve_output_path,
    resolve_output_paths,
    resolve_sector_card_path,
    validate_output_record_shape,
)
from investment_system.core.schema_registry import get_nested, load_yaml
from investment_system.pipelines.sector_research.load_project import (
    ProjectConfig,
    load_project,
)
from investment_system.pipelines.sector_research.load_project import main as _legacy_main

__all__ = [
    "PROJECTS_ROOT",
    "SCHEMAS_ROOT",
    "WORKSPACE_ROOT",
    "ProjectConfig",
    "ValidationWarning",
    "build_legacy_sector_map",
    "get_sector",
    "get_output_contract",
    "get_output_schema",
    "get_output_spec",
    "get_stocks_for_sector",
    "get_nested",
    "list_scoring_sectors",
    "list_output_types",
    "load_project",
    "load_yaml",
    "resolve_evidence_files_for_sector",
    "resolve_output_path",
    "resolve_output_paths",
    "resolve_sector_card_path",
    "resolve_sector_id",
    "safe_filename",
    "validate_output_record_shape",
]


def main() -> int:
    """Run the legacy project-loader CLI through the new core facade."""
    return _legacy_main()


if __name__ == "__main__":
    raise SystemExit(main())
