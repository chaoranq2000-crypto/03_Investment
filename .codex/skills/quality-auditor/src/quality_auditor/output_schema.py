"""Audit project-aware output schema and field contract readiness."""
from __future__ import annotations

import argparse
import ast
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from investment_system.core.project_loader import (
    WORKSPACE_ROOT,
    get_output_contract,
    list_output_types,
    load_project,
    resolve_output_path,
)


@dataclass
class Finding:
    severity: str
    code: str
    message: str
    file: str = ""


def _read_yaml(path: Path) -> tuple[dict[str, Any], str]:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}, ""
    except Exception as exc:  # noqa: BLE001
        return {}, str(exc)


def _extract_list_constant(content: str, name: str) -> list[str]:
    try:
        tree = ast.parse(content)
    except Exception:
        return []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                continue
            try:
                value = ast.literal_eval(node.value)
            except Exception:
                return []
            return [str(item) for item in value if isinstance(item, str)]
    return []


def _csv_header(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return next(csv.reader(f), [])


def _contract_field_set(contract: dict[str, Any]) -> set[str]:
    fields = set(contract.get("required_fields", []) or [])
    fields.update(contract.get("optional_fields", []) or [])
    fields.update(contract.get("legacy_display_fields", []) or [])
    return fields


def _audit_contract_definitions(config: Any, findings: list[Finding]) -> dict[str, int]:
    required_field_count = 0
    deprecated_field_count = 0
    legacy_display_field_count = 0
    for output_type in list_output_types(config):
        contract = get_output_contract(config, output_type)
        required = contract.get("required_fields", []) or []
        deprecated = contract.get("deprecated_fields", []) or []
        legacy_display = contract.get("legacy_display_fields", []) or []
        required_field_count += len(required)
        deprecated_field_count += len(deprecated)
        legacy_display_field_count += len(legacy_display)
        if not required:
            findings.append(Finding("ERROR", "OUTPUT_TYPE_REQUIRED_FIELDS_MISSING", f"{output_type} has no required_fields."))
        if output_type == "source_index" and "source_id" not in required:
            findings.append(Finding("ERROR", "SOURCE_INDEX_SOURCE_ID_NOT_REQUIRED", "source_index must require source_id."))
        if output_type == "score_table":
            for score in [
                "prosperity",
                "earnings_certainty",
                "valuation",
                "trading_comfort",
                "catalyst",
                "purity",
                "risk_control",
            ]:
                if f"{score}_score" in required and f"{score}_reason" not in required:
                    findings.append(
                        Finding("ERROR", "SCORE_REASON_NOT_REQUIRED", f"score_table {score}_score lacks required reason field.")
                    )
    return {
        "required_field_count": required_field_count,
        "deprecated_field_count": deprecated_field_count,
        "legacy_display_field_count": legacy_display_field_count,
    }


def _audit_run_research_fields(config: Any, findings: list[Finding]) -> dict[str, str]:
    path = WORKSPACE_ROOT / "investment_system" / "pipelines" / "run_research.py"
    content = path.read_text(encoding="utf-8")
    company_fields = _extract_list_constant(content, "COMPANY_TABLE_FIELDS")
    comparison_fields = _extract_list_constant(content, "COMPARISON_FIELDS")
    source_fields = _extract_list_constant(content, "SOURCE_FIELDS")
    status = "ok"

    checks = [
        ("company_table", company_fields, "COMPANY_TABLE_FIELDS"),
        ("sector_comparison_table", comparison_fields, "COMPARISON_FIELDS"),
        ("source_index", source_fields, "SOURCE_FIELDS"),
    ]
    for output_type, fields, constant in checks:
        if not fields:
            findings.append(Finding("ERROR", "FIELD_CONSTANT_MISSING", f"{constant} not found or not parseable.", str(path)))
            status = "error"
            continue
        contract = get_output_contract(config, output_type)
        allowed = _contract_field_set(contract)
        required = set(contract.get("required_fields", []) or [])
        missing_required = sorted(required - set(fields))
        extra = sorted(set(fields) - allowed)
        if missing_required:
            findings.append(
                Finding("ERROR", "FIELD_CONSTANT_REQUIRED_MISSING", f"{constant} missing required fields: {missing_required}", str(path))
            )
            status = "error"
        if extra:
            findings.append(Finding("WARNING", "FIELD_CONSTANT_EXTRA_FIELDS", f"{constant} has non-contract fields: {extra}", str(path)))
            if status == "ok":
                status = "warning"

    legacy_project_keys = [field for field in ("main_theme", "sub_theme") if field in company_fields]
    if legacy_project_keys:
        findings.append(
            Finding(
                "ERROR",
                "COMPANY_TABLE_LEGACY_PRIMARY_KEY",
                f"COMPANY_TABLE_FIELDS still contains legacy key fields: {legacy_project_keys}",
                str(path),
            )
        )
        status = "error"

    return {"company_table_contract_status": status}


def _audit_paths_and_legacy_calls(findings: list[Finding]) -> dict[str, int]:
    targets = [
        WORKSPACE_ROOT / "investment_system" / "pipelines" / "run_research.py",
        WORKSPACE_ROOT / "investment_system" / "pipelines" / "validate_outputs.py",
    ]
    hardcoded_count = 0
    for path in targets:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        for pattern in ("科技主线调研输出", "01_AI算力硬件"):
            count = content.count(pattern)
            hardcoded_count += count
            if count:
                severity = "WARNING" if "tools" in str(path) else "INFO"
                findings.append(
                    Finding(
                        severity,
                        "HARDCODED_OUTPUT_PATH_LITERAL",
                        f"found {count} literal occurrence(s) of {pattern}; verify legacy-only or loader-backed use.",
                        str(path),
                    )
                )
        if "THEME_REGISTRY_CSV" in content and "if args.project" in content:
            findings.append(
                Finding(
                    "WARNING",
                    "THEME_REGISTRY_CSV_PRESENT",
                    "THEME_REGISTRY_CSV remains in file; audit requires it stay outside project-aware primary path.",
                    str(path),
                )
            )
    return {"hardcoded_output_path_count": hardcoded_count}


def _audit_existing_outputs(config: Any, findings: list[Finding]) -> None:
    outputs = [
        ("company_table", Path(resolve_output_path(config, "company_table"))),
        ("sector_comparison_table", Path(resolve_output_path(config, "sector_comparison_table"))),
        ("source_index", Path(resolve_output_path(config, "source_index"))),
    ]
    formal_found = False
    for output_type, path in outputs:
        if not path.exists():
            continue
        formal_found = True
        header = _csv_header(path)
        contract = get_output_contract(config, output_type)
        required = set(contract.get("required_fields", []) or [])
        deprecated = set(contract.get("deprecated_fields", []) or [])
        missing = sorted(required - set(header))
        if missing:
            findings.append(Finding("ERROR", "FORMAL_OUTPUT_REQUIRED_FIELDS_MISSING", f"{output_type} missing fields: {missing}", str(path)))
        deprecated_present = sorted(deprecated.intersection(header))
        if deprecated_present:
            findings.append(Finding("ERROR", "FORMAL_OUTPUT_DEPRECATED_FIELDS", f"{output_type} has deprecated fields: {deprecated_present}", str(path)))
    if not formal_found:
        findings.append(Finding("INFO", "NO_FORMAL_OUTPUT_FILES", "No formal output CSV files found; structural contract audit only."))


def _validate_outputs_contract_status() -> tuple[str, Path]:
    candidate_paths = [
        WORKSPACE_ROOT / "investment_system" / "pipelines" / "validate_outputs.py",
        WORKSPACE_ROOT / ".codex" / "skills" / "quality-auditor" / "src" / "quality_auditor" / "validate_outputs.py",
    ]
    fallback = candidate_paths[0]
    for path in candidate_paths:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        if "Output contract loaded" in content and "validate_csv_contract" in content:
            return "ok", path
    return "missing", fallback


def audit_project(project_id: str, write_report: bool = True) -> tuple[list[Finding], dict[str, Any]]:
    findings: list[Finding] = []
    config = load_project(project_id, silent=True, strict=False)
    project_dir = WORKSPACE_ROOT / "investment_system" / "research" / "projects" / project_id
    output_spec_path = project_dir / "output_spec.yaml"
    output_schema_path = WORKSPACE_ROOT / "investment_system" / "research" / "schemas" / "output.schema.yaml"

    output_spec, spec_error = _read_yaml(output_spec_path)
    output_schema, schema_error = _read_yaml(output_schema_path)
    if spec_error:
        findings.append(Finding("ERROR", "OUTPUT_SPEC_PARSE_ERROR", spec_error, str(output_spec_path)))
    if schema_error:
        findings.append(Finding("ERROR", "OUTPUT_SCHEMA_PARSE_ERROR", schema_error, str(output_schema_path)))
    if not output_spec:
        findings.append(Finding("ERROR", "OUTPUT_SPEC_MISSING", "output_spec.yaml missing or empty.", str(output_spec_path)))
    if not output_schema:
        findings.append(Finding("ERROR", "OUTPUT_SCHEMA_MISSING", "output.schema.yaml missing or empty.", str(output_schema_path)))

    output_types = list_output_types(config) if output_schema else []
    contract_counts = _audit_contract_definitions(config, findings) if output_schema else {
        "required_field_count": 0,
        "deprecated_field_count": 0,
        "legacy_display_field_count": 0,
    }
    field_status = _audit_run_research_fields(config, findings) if output_schema else {"company_table_contract_status": "error"}
    path_counts = _audit_paths_and_legacy_calls(findings)
    _audit_existing_outputs(config, findings)

    validate_status, validate_path = _validate_outputs_contract_status()
    if validate_status != "ok":
        findings.append(Finding("ERROR", "VALIDATE_OUTPUTS_CONTRACT_MISSING", "validate_outputs.py does not load output contract.", str(validate_path)))

    summary = {
        "project_id": project_id,
        "output_type_count": len(output_types),
        "required_field_count": contract_counts["required_field_count"],
        "deprecated_field_count": contract_counts["deprecated_field_count"],
        "legacy_display_field_count": contract_counts["legacy_display_field_count"],
        "hardcoded_output_path_count": path_counts["hardcoded_output_path_count"],
        "company_table_contract_status": field_status["company_table_contract_status"],
        "validate_outputs_contract_status": validate_status,
    }
    if write_report:
        _write_report(project_id, findings, summary)
    return findings, summary


def _counts(findings: list[Finding]) -> dict[str, int]:
    return {
        "ERROR": sum(1 for f in findings if f.severity == "ERROR"),
        "WARNING": sum(1 for f in findings if f.severity == "WARNING"),
        "INFO": sum(1 for f in findings if f.severity == "INFO"),
    }


def _write_report(project_id: str, findings: list[Finding], summary: dict[str, Any]) -> None:
    counts = _counts(findings)
    audit_dir = WORKSPACE_ROOT / "investment_system" / "research" / "projects" / project_id / "audits"
    audit_dir.mkdir(parents=True, exist_ok=True)
    path = audit_dir / "output_schema_audit.md"
    lines = [
        "# Output Schema Audit - Phase 1E-e-a",
        "",
        f"Project: `{project_id}`",
        "",
        "Scope: engineering output contract audit only. No formal research output is generated.",
        "",
        "## Summary",
        "",
        f"- ERROR: {counts['ERROR']}",
        f"- WARNING: {counts['WARNING']}",
        f"- INFO: {counts['INFO']}",
        f"- output_type_count: {summary['output_type_count']}",
        f"- required_field_count: {summary['required_field_count']}",
        f"- deprecated_field_count: {summary['deprecated_field_count']}",
        f"- legacy_display_field_count: {summary['legacy_display_field_count']}",
        f"- hardcoded_output_path_count: {summary['hardcoded_output_path_count']}",
        f"- company_table_contract_status: {summary['company_table_contract_status']}",
        f"- validate_outputs_contract_status: {summary['validate_outputs_contract_status']}",
        "",
        "## Findings",
        "",
    ]
    for severity in ["ERROR", "WARNING", "INFO"]:
        rows = [f for f in findings if f.severity == severity]
        if not rows:
            continue
        lines.append(f"### {severity}")
        lines.append("")
        for f in rows:
            location = f" (`{f.file}`)" if f.file else ""
            lines.append(f"- `{f.code}`{location}: {f.message}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _print_report(findings: list[Finding], summary: dict[str, Any]) -> None:
    counts = _counts(findings)
    print("Output Schema Audit")
    print("=" * 60)
    print(f"project_id                       : {summary['project_id']}")
    print(f"ERROR                            : {counts['ERROR']}")
    print(f"WARNING                          : {counts['WARNING']}")
    print(f"INFO                             : {counts['INFO']}")
    print(f"output_type_count                : {summary['output_type_count']}")
    print(f"required_field_count             : {summary['required_field_count']}")
    print(f"deprecated_field_count           : {summary['deprecated_field_count']}")
    print(f"legacy_display_field_count       : {summary['legacy_display_field_count']}")
    print(f"hardcoded_output_path_count      : {summary['hardcoded_output_path_count']}")
    print(f"company_table_contract_status    : {summary['company_table_contract_status']}")
    print(f"validate_outputs_contract_status : {summary['validate_outputs_contract_status']}")
    print()
    for severity in ["ERROR", "WARNING", "INFO"]:
        rows = [f for f in findings if f.severity == severity]
        if not rows:
            continue
        print(f"{severity}s")
        for f in rows:
            location = f" ({f.file})" if f.file else ""
            print(f"  [{f.code}]{location} {f.message}")
        print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit project-aware output schema readiness.")
    parser.add_argument("--project", required=True, help="Project ID under research/projects/")
    args = parser.parse_args(argv)
    findings, summary = audit_project(args.project, write_report=True)
    _print_report(findings, summary)
    return 1 if any(f.severity == "ERROR" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
