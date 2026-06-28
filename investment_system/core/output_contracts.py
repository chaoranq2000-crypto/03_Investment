"""Shared output-contract helpers for project-aware workflows."""

from __future__ import annotations

from typing import Any

import yaml

from investment_system.core.constants import SCHEMAS_ROOT
from investment_system.core.path_resolver import (
    resolve_output_paths,
    resolve_sector_card_path,
)

__all__ = [
    "get_output_contract",
    "get_output_schema",
    "get_output_spec",
    "list_output_types",
    "resolve_output_path",
    "resolve_output_paths",
    "validate_output_record_shape",
]


def get_output_spec(config: Any) -> dict[str, Any]:
    """Return project output_spec.yaml as loaded by the project loader."""
    return config.raw.get("output_spec", {}) or {}


def get_output_schema() -> dict[str, Any]:
    """Return the canonical output.schema.yaml contract."""
    path = SCHEMAS_ROOT / "output.schema.yaml"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def list_output_types(config: Any) -> list[str]:
    """List output types known to the canonical output contract."""
    schema = get_output_schema()
    output_types = schema.get("output_types", {}) or {}
    return sorted(output_types)


def get_output_contract(config: Any, output_type: str) -> dict[str, Any]:
    """Return a single canonical output contract."""
    schema = get_output_schema()
    contract = (schema.get("output_types", {}) or {}).get(output_type)
    if not contract:
        raise KeyError(f"output_type '{output_type}' not found in output.schema.yaml")
    result = dict(contract)
    result["output_type"] = output_type
    result["schema_version"] = schema.get("schema_version", "")
    return result


def _table_file_by_name(config: Any, file_name: str):
    return config.total_tables_dir / file_name


def resolve_output_path(
    config: Any,
    output_type: str,
    sector_id: str | None = None,
) -> str:
    """Resolve project-aware output path for a known output type."""
    if output_type == "sector_card":
        if not sector_id:
            raise ValueError("sector_id is required for sector_card output path")
        return str(resolve_sector_card_path(config, sector_id))
    if output_type == "company_table":
        return str(_table_file_by_name(config, "代表公司财务估值总表.csv"))
    if output_type == "sector_comparison_table":
        return str(_table_file_by_name(config, "科技细分方向横向比较表.csv"))
    if output_type == "source_index":
        return str(_table_file_by_name(config, "数据来源索引.csv"))
    if output_type == "missing_data_log":
        return str(config.logs_dir / "缺失数据清单.md")
    if output_type == "conflict_data_log":
        return str(config.logs_dir / "冲突数据清单.md")
    if output_type == "score_table":
        return str(_table_file_by_name(config, "科技细分方向横向比较表.csv"))
    raise KeyError(f"Unknown output_type '{output_type}'")


def validate_output_record_shape(
    config: Any,
    output_type: str,
    record: dict[str, Any],
) -> dict[str, Any]:
    """Validate a generated output record against the canonical output contract."""
    errors: list[str] = []
    warnings: list[str] = []
    contract = get_output_contract(config, output_type)
    required = list(contract.get("required_fields", []) or [])
    deprecated = set(contract.get("deprecated_fields", []) or [])
    legacy_display = set(contract.get("legacy_display_fields", []) or [])
    primary_keys = set(contract.get("primary_key", []) or [])
    optional = set(contract.get("optional_fields", []) or [])
    allowed_placeholders = set(
        (get_output_schema().get("empty_value_policy", {}) or {})
        .get("allowed_placeholders", []) or []
    )

    missing_required = sorted(
        field for field in required
        if field not in record or record.get(field) is None or str(record.get(field)).strip() == ""
    )
    for field in missing_required:
        errors.append(f"{output_type} record missing required field '{field}'")

    deprecated_fields_present = sorted(deprecated.intersection(record))
    for field in deprecated_fields_present:
        warnings.append(f"{output_type} record contains deprecated field '{field}'")

    legacy_fields_present = sorted(legacy_display.intersection(record))
    forbidden = {"main_theme", "sub_theme", "legacy_theme_name"}
    for key in sorted(primary_keys.intersection(forbidden)):
        errors.append(f"{output_type} contract uses legacy field '{key}' as primary key")

    for key in sorted(forbidden.intersection(record)):
        if key in primary_keys:
            errors.append(f"{output_type} record uses legacy field '{key}' as primary key")
        elif key not in legacy_display:
            warnings.append(f"{output_type} record contains legacy field '{key}' outside legacy_display_fields")

    empty_required = [
        field for field in required
        if str(record.get(field, "")).strip() in allowed_placeholders
        and str(record.get(field, "")).strip() != ""
    ]
    for field in empty_required:
        warnings.append(f"{output_type} required field '{field}' uses placeholder value '{record.get(field)}'")

    source_status: dict[str, Any] = {"status": "not_required"}
    source_reqs = contract.get("source_evidence_requirements", {}) or {}
    if source_reqs.get("source_ids_required") and "source_ids" not in record:
        errors.append(f"{output_type} requires source_ids field")
        source_status["status"] = "missing_source_ids"
    elif source_reqs.get("source_ids_required"):
        source_status["status"] = "source_ids_present"

    if source_reqs.get("source_id_required") and "source_id" not in record:
        errors.append(f"{output_type} requires source_id field")
        source_status["status"] = "missing_source_id"
    elif source_reqs.get("source_id_required"):
        source_status["status"] = "source_id_present"

    if output_type == "source_index" and "source_id" not in record:
        errors.append("source_index record missing source_id")

    if output_type == "score_table":
        score_fields = [
            field for field in required
            if field.endswith("_score") and field != "total_score"
        ]
        missing_reasons = [
            field.replace("_score", "_reason")
            for field in score_fields
            if field.replace("_score", "_reason") not in record
            or str(record.get(field.replace("_score", "_reason"), "")).strip() == ""
        ]
        if missing_reasons:
            errors.append(f"score_table missing score reason fields: {', '.join(missing_reasons)}")

    if output_type == "missing_data_log":
        for field in ["output_type", "sector_id", "missing_field", "severity", "reason"]:
            if field not in record or str(record.get(field, "")).strip() == "":
                errors.append(f"missing_data_log missing canonical field '{field}'")

    if output_type == "conflict_data_log":
        for field in ["output_type", "sector_id", "field", "conflicting_values", "source_ids"]:
            if field not in record or str(record.get(field, "")).strip() == "":
                errors.append(f"conflict_data_log missing canonical field '{field}'")

    contract_fields = set(required) | optional | legacy_display
    extra_fields = sorted(set(record) - contract_fields - deprecated)
    if extra_fields:
        warnings.append(f"{output_type} record has fields outside contract: {extra_fields}")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "output_type": output_type,
        "missing_required_fields": missing_required,
        "deprecated_fields_present": deprecated_fields_present,
        "legacy_fields_present": legacy_fields_present,
        "source_evidence_status": source_status,
    }
