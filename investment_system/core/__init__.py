"""Shared runtime core for project-aware investment research workflows.

This package is the stable import surface for project-local skill modules.
Runtime entry points are expected to use canonical project_id and sector_id
inputs through the skill CLIs.
"""

from __future__ import annotations

__all__ = [
    "PROJECTS_ROOT",
    "AI_APP_FORBIDDEN_PARENTCHAINS",
    "MD_SCAN_EXCLUDE_DIRS",
    "MD_SCAN_EXCLUDE_FILES",
    "ResearchRuntimePaths",
    "REQUIRED_OUTPUT_SPEC_FIELDS",
    "REQUIRED_PROJECT_FILES",
    "SCHEMAS_ROOT",
    "SEED_FORBIDDEN_ACTIONS",
    "SEED_FORBIDDEN_STATUSES",
    "SEED_FORBIDDEN_TYPES",
    "SEED_MANDATORY_NOT_ALLOWED",
    "STOCK_CODE_PATTERN",
    "WORKSPACE_ROOT",
    "ProjectConfig",
    "SectorContext",
    "ValidationWarning",
    "check_path_safety",
    "compute_coverage_status",
    "get_nested",
    "get_sector",
    "get_output_contract",
    "get_output_schema",
    "get_stocks_for_sector",
    "list_project_sectors_by_priority",
    "list_scoring_sectors",
    "list_output_types",
    "load_project",
    "load_yaml",
    "resolve_output_path",
    "resolve_output_paths",
    "resolve_sector_context",
    "resolve_evidence_files_for_sector",
    "resolve_sector_card_path",
    "resolve_sector_id",
    "safe_filename",
    "safe_output_name",
    "validate_output_record_shape",
]


def __getattr__(name: str):
    if name in {"PROJECTS_ROOT", "SCHEMAS_ROOT", "WORKSPACE_ROOT"}:
        from investment_system.core import constants

        return getattr(constants, name)
    if name in {
        "AI_APP_FORBIDDEN_PARENTCHAINS",
        "MD_SCAN_EXCLUDE_DIRS",
        "MD_SCAN_EXCLUDE_FILES",
        "REQUIRED_OUTPUT_SPEC_FIELDS",
        "REQUIRED_PROJECT_FILES",
        "SEED_FORBIDDEN_ACTIONS",
        "SEED_FORBIDDEN_STATUSES",
        "SEED_FORBIDDEN_TYPES",
        "SEED_MANDATORY_NOT_ALLOWED",
        "STOCK_CODE_PATTERN",
    }:
        from investment_system.core import project_contracts

        return getattr(project_contracts, name)
    if name in {
        "ResearchRuntimePaths",
        "SectorContext",
        "check_path_safety",
        "compute_coverage_status",
        "list_project_sectors_by_priority",
        "resolve_sector_context",
        "safe_output_name",
    }:
        from investment_system.core import sector_runtime

        return getattr(sector_runtime, name)
    if name in {
        "safe_filename",
        "resolve_output_paths",
        "resolve_sector_card_path",
    }:
        from investment_system.core import path_resolver

        return getattr(path_resolver, name)
    if name in {
        "get_output_contract",
        "get_output_schema",
        "list_output_types",
        "resolve_output_path",
        "validate_output_record_shape",
    }:
        from investment_system.core import output_contracts

        return getattr(output_contracts, name)
    if name in {
        "get_sector",
        "get_stocks_for_sector",
        "list_scoring_sectors",
        "resolve_evidence_files_for_sector",
        "resolve_sector_id",
    }:
        from investment_system.core import evidence_registry

        return getattr(evidence_registry, name)
    if name in {
        "get_nested",
        "load_yaml",
    }:
        from investment_system.core import schema_registry

        return getattr(schema_registry, name)
    if name in {
        "ValidationWarning",
    }:
        from investment_system.core import audit_types

        return getattr(audit_types, name)
    if name in {
        "ProjectConfig",
        "load_project",
    }:
        from investment_system.core import project_loader

        return getattr(project_loader, name)
    raise AttributeError(f"module 'investment_system.core' has no attribute {name!r}")
