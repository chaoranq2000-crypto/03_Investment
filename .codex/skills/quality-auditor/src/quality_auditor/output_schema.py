"""Audit project-aware output schema and field contract readiness."""
from __future__ import annotations

import argparse
import csv
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


def _csv_header(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return next(csv.reader(f), [])


def _audit_contract_definitions(config: Any, findings: list[Finding]) -> dict[str, int]:
    required_field_count = 0
    optional_field_count = 0
    for output_type in list_output_types(config):
        contract = get_output_contract(config, output_type)
        required = contract.get("required_fields", []) or []
        optional = contract.get("optional_fields", []) or []
        required_field_count += len(required)
        optional_field_count += len(optional)
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
        "optional_field_count": optional_field_count,
    }


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
        missing = sorted(required - set(header))
        if missing:
            findings.append(Finding("ERROR", "FORMAL_OUTPUT_REQUIRED_FIELDS_MISSING", f"{output_type} missing fields: {missing}", str(path)))
    if not formal_found:
        findings.append(Finding("INFO", "NO_FORMAL_OUTPUT_FILES", "No formal output CSV files found; structural contract audit only."))


def _validate_outputs_contract_status() -> tuple[str, Path]:
    candidate_paths = [
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
        "optional_field_count": 0,
    }
    field_status = {"output_contract_status": "ok" if output_schema else "error"}
    _audit_existing_outputs(config, findings)

    validate_status, validate_path = _validate_outputs_contract_status()
    if validate_status != "ok":
        findings.append(Finding("ERROR", "VALIDATE_OUTPUTS_CONTRACT_MISSING", "validate_outputs.py does not load output contract.", str(validate_path)))

    summary = {
        "project_id": project_id,
        "output_type_count": len(output_types),
        "required_field_count": contract_counts["required_field_count"],
        "optional_field_count": contract_counts["optional_field_count"],
        "output_contract_status": field_status["output_contract_status"],
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
        f"- optional_field_count: {summary['optional_field_count']}",
        f"- output_contract_status: {summary['output_contract_status']}",
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
    print(f"optional_field_count             : {summary['optional_field_count']}")
    print(f"output_contract_status           : {summary['output_contract_status']}")
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
