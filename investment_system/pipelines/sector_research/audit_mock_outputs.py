"""Audit mock output generation against the canonical output contract."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from investment_system.pipelines.sector_research.build_mock_outputs import (
    CSV_OUTPUT_TYPES,
    MOCK_FILENAMES,
    MOCK_MARKER,
    build_mock_records,
    get_mock_output_dir,
    render_sector_card_front_matter,
    validate_records,
)
from investment_system.pipelines.sector_research.load_project import (
    WORKSPACE_ROOT,
    ProjectConfig,
    get_output_contract,
    list_output_types,
    load_project,
)


@dataclass
class Finding:
    severity: str
    code: str
    message: str
    file: str = ""


def _counts(findings: list[Finding]) -> dict[str, int]:
    return {
        "ERROR": sum(1 for f in findings if f.severity == "ERROR"),
        "WARNING": sum(1 for f in findings if f.severity == "WARNING"),
        "INFO": sum(1 for f in findings if f.severity == "INFO"),
    }


def _field_order(config: ProjectConfig, output_type: str) -> list[str]:
    contract = get_output_contract(config, output_type)
    fields: list[str] = []
    for key in ("required_fields", "optional_fields"):
        for field in contract.get(key, []) or []:
            if field not in fields:
                fields.append(field)
    return fields


def _audit_record_shapes(
    config: ProjectConfig,
    records: dict[str, dict[str, Any]],
    findings: list[Finding],
) -> dict[str, int]:
    results = validate_records(config, records)
    pass_count = 0
    fail_count = 0
    deprecated_count = 0

    for output_type in list_output_types(config):
        result = results.get(output_type, {})
        if result.get("ok"):
            pass_count += 1
        else:
            fail_count += 1
            for error in result.get("errors", []):
                findings.append(Finding("ERROR", "MOCK_RECORD_SHAPE_FAILED", error, output_type))
        deprecated = result.get("deprecated_fields_present", []) or []
        deprecated_count += len(deprecated)
        for field in deprecated:
            findings.append(Finding("ERROR", "MOCK_DEPRECATED_FIELD_PRESENT", f"{output_type} contains deprecated field {field}", output_type))

    return {
        "record_shape_pass_count": pass_count,
        "record_shape_fail_count": fail_count,
        "deprecated_field_violation_count": deprecated_count,
    }


def _audit_csv_headers(config: ProjectConfig, records: dict[str, dict[str, Any]], findings: list[Finding]) -> int:
    pass_count = 0
    for output_type in CSV_OUTPUT_TYPES:
        expected = _field_order(config, output_type)
        record = records.get(output_type, {})
        missing_in_record = [field for field in expected if field not in record and field in (get_output_contract(config, output_type).get("required_fields", []) or [])]
        if missing_in_record:
            findings.append(Finding("ERROR", "MOCK_CSV_REQUIRED_FIELD_MISSING", f"{output_type} record missing required header fields: {missing_in_record}", output_type))
            continue
        if expected:
            pass_count += 1
    return pass_count


def _audit_markdown_front_matter(record: dict[str, Any], findings: list[Finding]) -> int:
    text = render_sector_card_front_matter(record)
    required_tokens = ["---", "project_id:", "sector_id:", "source_ids:", "mock_only: true", MOCK_MARKER]
    missing = [token for token in required_tokens if token not in text]
    if missing:
        findings.append(Finding("ERROR", "MOCK_MARKDOWN_FRONT_MATTER_INVALID", f"sector_card front matter missing: {missing}", "sector_card"))
        return 0
    return 1


def _audit_semantic_requirements(records: dict[str, dict[str, Any]], findings: list[Finding]) -> None:
    company = records.get("company_table", {})
    if not company.get("sector_id") or not company.get("stock_code"):
        findings.append(Finding("ERROR", "MOCK_COMPANY_CANONICAL_KEYS_MISSING", "company_table must include sector_id and stock_code."))

    comparison = records.get("sector_comparison_table", {})
    if not comparison.get("sector_id"):
        findings.append(Finding("ERROR", "MOCK_COMPARISON_SECTOR_ID_MISSING", "sector_comparison_table must include sector_id."))

    source = records.get("source_index", {})
    if not source.get("source_id"):
        findings.append(Finding("ERROR", "MOCK_SOURCE_ID_MISSING", "source_index must include source_id."))

    score = records.get("score_table", {})
    score_fields = [field for field in score if field.endswith("_score") and field != "total_score"]
    for field in score_fields:
        reason = field.replace("_score", "_reason")
        if not score.get(reason):
            findings.append(Finding("ERROR", "MOCK_SCORE_REASON_MISSING", f"score_table {field} lacks {reason}."))
    if MOCK_MARKER not in " ".join(str(v) for v in score.values()):
        findings.append(Finding("ERROR", "MOCK_SCORE_MARKER_MISSING", "score_table must contain the mock marker."))

    missing_log = records.get("missing_data_log", {})
    for field in ["severity", "reason"]:
        if not missing_log.get(field):
            findings.append(Finding("ERROR", "MOCK_MISSING_LOG_FIELD_MISSING", f"missing_data_log missing {field}."))

    conflict_log = records.get("conflict_data_log", {})
    for field in ["source_ids", "conflicting_values"]:
        if not conflict_log.get(field):
            findings.append(Finding("ERROR", "MOCK_CONFLICT_LOG_FIELD_MISSING", f"conflict_data_log missing {field}."))

    for output_type, record in records.items():
        for legacy_key in ["main_theme", "sub_theme"]:
            if legacy_key in record:
                findings.append(Finding("ERROR", "MOCK_LEGACY_KEY_PRESENT", f"{output_type} contains legacy key {legacy_key}."))


def _read_csv_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return next(csv.reader(f), [])


def _audit_existing_mock_files(config: ProjectConfig, findings: list[Finding]) -> dict[str, int]:
    mock_dir = get_mock_output_dir(config)
    mock_file_count = 0
    if mock_dir.exists():
        for name in MOCK_FILENAMES.values():
            path = mock_dir / name
            if not path.exists():
                continue
            mock_file_count += 1
            resolved = path.resolve()
            if not str(resolved).startswith(str(mock_dir.resolve())):
                findings.append(Finding("ERROR", "MOCK_FILE_OUTSIDE_AUDIT_DIR", f"mock file outside audit dir: {resolved}", str(path)))
            if str(resolved).startswith(str(config.output_root.resolve())):
                findings.append(Finding("ERROR", "MOCK_FILE_IN_FORMAL_OUTPUT_ROOT", f"mock file written to formal output root: {resolved}", str(path)))
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            if MOCK_MARKER not in text:
                findings.append(Finding("ERROR", "MOCK_FILE_MARKER_MISSING", f"mock file lacks marker {MOCK_MARKER}", str(path)))

    formal_violation_count = 0
    if config.output_root.exists():
        for path in config.output_root.rglob("mock_*"):
            formal_violation_count += 1
            findings.append(Finding("ERROR", "MOCK_FILE_IN_FORMAL_OUTPUT_ROOT", f"mock file found in formal output root: {path}", str(path)))

    return {
        "mock_file_count": mock_file_count,
        "formal_output_write_violation_count": formal_violation_count,
    }


def audit_project(project_id: str, write_report: bool = True, sector_id: str | None = None) -> tuple[list[Finding], dict[str, Any]]:
    config = load_project(project_id, create_dirs=False, strict=False, silent=True)
    findings: list[Finding] = []
    records = build_mock_records(config, sector_id)
    output_types = list_output_types(config)

    missing_types = [output_type for output_type in output_types if output_type not in records]
    for output_type in missing_types:
        findings.append(Finding("ERROR", "MOCK_OUTPUT_TYPE_MISSING", f"No mock record for output_type {output_type}."))

    shape_counts = _audit_record_shapes(config, records, findings)
    csv_header_pass_count = _audit_csv_headers(config, records, findings)
    markdown_front_matter_pass_count = _audit_markdown_front_matter(records.get("sector_card", {}), findings)
    _audit_semantic_requirements(records, findings)
    file_counts = _audit_existing_mock_files(config, findings)

    counts = _counts(findings)
    summary = {
        **counts,
        "project_id": project_id,
        "sector_id": sector_id,
        "output_type_count": len(output_types),
        "mock_record_count": len(records),
        "mock_file_count": file_counts["mock_file_count"],
        "record_shape_pass_count": shape_counts["record_shape_pass_count"],
        "record_shape_fail_count": shape_counts["record_shape_fail_count"],
        "csv_header_pass_count": csv_header_pass_count,
        "markdown_front_matter_pass_count": markdown_front_matter_pass_count,
        "deprecated_field_violation_count": shape_counts["deprecated_field_violation_count"],
        "formal_output_write_violation_count": file_counts["formal_output_write_violation_count"],
        "mock_output_dir": str(get_mock_output_dir(config)),
    }

    if not findings:
        findings.append(Finding("INFO", "MOCK_OUTPUTS_READY", "All mock output records pass contract shape validation."))
        summary.update(_counts(findings))

    if write_report:
        _write_report(project_id, findings, summary)

    return findings, summary


def _write_report(project_id: str, findings: list[Finding], summary: dict[str, Any]) -> None:
    audit_dir = WORKSPACE_ROOT / "investment_system" / "research" / "projects" / project_id / "audits"
    audit_dir.mkdir(parents=True, exist_ok=True)
    path = audit_dir / "mock_output_audit.md"
    lines = [
        "# Mock Output Audit — Phase 1E-e-b",
        "",
        f"Project: `{project_id}`",
        f"Sector ID: `{summary.get('sector_id', 'default')}`",
        "",
        "Scope: engineering mock-output audit only. No formal research output is generated.",
        "",
        "## Summary",
    ]
    for key in [
        "ERROR", "WARNING", "INFO", "output_type_count", "mock_record_count",
        "mock_file_count", "record_shape_pass_count", "record_shape_fail_count",
        "csv_header_pass_count", "markdown_front_matter_pass_count",
        "deprecated_field_violation_count", "formal_output_write_violation_count",
        "mock_output_dir",
    ]:
        lines.append(f"- {key}: {summary.get(key)}")
    lines.extend(["", "## Findings"])
    for finding in findings:
        loc = f" ({finding.file})" if finding.file else ""
        lines.append(f"- {finding.severity} [{finding.code}]{loc}: {finding.message}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _print_summary(findings: list[Finding], summary: dict[str, Any]) -> None:
    print("Mock Output Audit")
    print("=" * 60)
    print(f"project_id: {summary.get('project_id')}")
    print(f"sector_id: {summary.get('sector_id')}")
    print(f"ERROR: {summary.get('ERROR')}")
    print(f"WARNING: {summary.get('WARNING')}")
    print(f"INFO: {summary.get('INFO')}")
    for key in [
        "output_type_count", "mock_record_count",
        "mock_file_count", "record_shape_pass_count", "record_shape_fail_count",
        "csv_header_pass_count", "markdown_front_matter_pass_count",
        "deprecated_field_violation_count", "formal_output_write_violation_count",
    ]:
        print(f"{key:40}: {summary.get(key)}")
    if findings:
        print()
        print("Findings")
        for finding in findings:
            loc = f" ({finding.file})" if finding.file else ""
            print(f"  [{finding.severity}] {finding.code}{loc}: {finding.message}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit project-aware mock output generation.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--sector-id", default=None, help="Canonical sector_id for mock output audit.")
    args = parser.parse_args(argv)
    findings, summary = audit_project(args.project, write_report=True, sector_id=args.sector_id)
    _print_summary(findings, summary)
    return 1 if summary["ERROR"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
