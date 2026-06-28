"""Audit project-aware generator preview outputs."""

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
    validate_output_record_shape,
)
from research_writer.output_writers import (
    CSV_OUTPUT_TYPES,
    GENERATOR_PREVIEW_FILENAMES,
    PREVIEW_MARKER,
    PREVIEW_RATING,
    build_generator_preview_records,
    get_generator_preview_dir,
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


def _field_order(config: Any, output_type: str) -> list[str]:
    contract = get_output_contract(config, output_type)
    fields: list[str] = []
    for key in ("required_fields", "optional_fields"):
        for field in contract.get(key, []) or []:
            if field not in fields:
                fields.append(field)
    return fields


def _read_csv_row(path: Path) -> tuple[list[str], dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        row = next(reader, {})
    return header, row


def _audit_preview_files(config: Any, findings: list[Finding]) -> dict[str, int]:
    preview_dir = get_generator_preview_dir(config)
    preview_file_count = 0
    record_shape_pass_count = 0
    record_shape_fail_count = 0
    csv_header_pass_count = 0
    source_evidence_field_pass_count = 0
    canonical_missing_conflict_log_pass_count = 0
    preview_score_table_pass_count = 0
    investment_conclusion_violation_count = 0
    markdown_front_matter_pass_count = 0

    if not preview_dir.exists():
        findings.append(Finding("ERROR", "GENERATOR_PREVIEW_DIR_MISSING", f"Preview directory not found: {preview_dir}", str(preview_dir)))
        return {
            "preview_file_count": 0,
            "record_shape_pass_count": 0,
            "record_shape_fail_count": 0,
            "csv_header_pass_count": 0,
            "markdown_front_matter_pass_count": 0,
            "source_evidence_field_pass_count": 0,
            "canonical_missing_conflict_log_pass_count": 0,
            "preview_score_table_pass_count": 0,
            "investment_conclusion_violation_count": 0,
        }

    output_root = config.output_root.resolve()
    preview_root = preview_dir.resolve()

    for output_type in CSV_OUTPUT_TYPES:
        path = preview_dir / GENERATOR_PREVIEW_FILENAMES[output_type]
        if not path.exists():
            findings.append(Finding("ERROR", "GENERATOR_PREVIEW_FILE_MISSING", f"Missing preview file for {output_type}.", str(path)))
            continue
        preview_file_count += 1
        resolved = path.resolve()
        if not str(resolved).startswith(str(preview_root)):
            findings.append(Finding("ERROR", "GENERATOR_PREVIEW_OUTSIDE_AUDIT_DIR", f"Preview file outside audit dir: {resolved}", str(path)))
        if str(resolved).startswith(str(output_root)):
            findings.append(Finding("ERROR", "GENERATOR_PREVIEW_IN_FORMAL_OUTPUT_ROOT", f"Preview file in formal output root: {resolved}", str(path)))

        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        if PREVIEW_MARKER not in text:
            findings.append(Finding("ERROR", "GENERATOR_PREVIEW_MARKER_MISSING", f"{output_type} lacks preview marker.", str(path)))
        for forbidden in ("建仓评级", "买入评级", "正式投资结论"):
            if forbidden in text:
                investment_conclusion_violation_count += 1
                findings.append(Finding("ERROR", "INVESTMENT_CONCLUSION_VIOLATION", f"{output_type} contains forbidden phrase {forbidden}.", str(path)))

        header, row = _read_csv_row(path)
        expected = _field_order(config, output_type)
        missing_header = [field for field in expected if field not in header]
        if missing_header:
            findings.append(Finding("ERROR", "GENERATOR_PREVIEW_CSV_HEADER_MISMATCH", f"{output_type} missing header fields: {missing_header}", str(path)))
        else:
            csv_header_pass_count += 1

        result = validate_output_record_shape(config, output_type, row)
        if result.get("ok"):
            record_shape_pass_count += 1
        else:
            record_shape_fail_count += 1
            for error in result.get("errors", []):
                findings.append(Finding("ERROR", "GENERATOR_PREVIEW_RECORD_SHAPE_FAILED", error, str(path)))

        if row.get("source_ids") or row.get("source_id"):
            if row.get("evidence_ids") or row.get("evidence_id") or output_type == "source_index":
                source_evidence_field_pass_count += 1
        else:
            findings.append(Finding("ERROR", "GENERATOR_PREVIEW_SOURCE_FIELD_MISSING", f"{output_type} lacks source field.", str(path)))

        if output_type == "missing_data_log":
            required = ["project_id", "output_type", "sector_id", "stock_code", "missing_field", "severity", "reason", "source_ids", "notes"]
            if all(row.get(field) for field in required):
                canonical_missing_conflict_log_pass_count += 1
            else:
                findings.append(Finding("ERROR", "MISSING_LOG_CANONICAL_SHAPE_FAILED", "missing_data_log lacks canonical fields.", str(path)))

        if output_type == "conflict_data_log":
            required = ["project_id", "output_type", "sector_id", "stock_code", "field", "conflicting_values", "source_ids", "severity", "resolution_status", "notes"]
            if all(row.get(field) for field in required):
                canonical_missing_conflict_log_pass_count += 1
            else:
                findings.append(Finding("ERROR", "CONFLICT_LOG_CANONICAL_SHAPE_FAILED", "conflict_data_log lacks canonical fields.", str(path)))

        if output_type == "score_table":
            if row.get("rating") == PREVIEW_RATING and PREVIEW_MARKER in text:
                preview_score_table_pass_count += 1
            else:
                findings.append(Finding("ERROR", "PREVIEW_SCORE_TABLE_RATING_INVALID", "score_table must use preview-only rating.", str(path)))

        if "main_theme" in header or "sub_theme" in header:
            findings.append(Finding("ERROR", "LEGACY_PRIMARY_KEY_IN_PREVIEW", f"{output_type} contains legacy key field.", str(path)))

    card_path = preview_dir / GENERATOR_PREVIEW_FILENAMES["sector_card"]
    if not card_path.exists():
        findings.append(Finding("ERROR", "GENERATOR_PREVIEW_FILE_MISSING", "Missing preview sector_card.", str(card_path)))
    else:
        preview_file_count += 1
        resolved = card_path.resolve()
        if not str(resolved).startswith(str(preview_root)):
            findings.append(Finding("ERROR", "GENERATOR_PREVIEW_OUTSIDE_AUDIT_DIR", f"Preview card outside audit dir: {resolved}", str(card_path)))
        if str(resolved).startswith(str(output_root)):
            findings.append(Finding("ERROR", "GENERATOR_PREVIEW_IN_FORMAL_OUTPUT_ROOT", f"Preview card in formal output root: {resolved}", str(card_path)))
        text = card_path.read_text(encoding="utf-8", errors="ignore")
        if PREVIEW_MARKER not in text:
            findings.append(Finding("ERROR", "GENERATOR_PREVIEW_MARKER_MISSING", "sector_card lacks preview marker.", str(card_path)))
        if text.startswith("---") and "preview_only: true" in text and "source_ids:" in text:
            markdown_front_matter_pass_count = 1
        else:
            findings.append(Finding("ERROR", "GENERATOR_PREVIEW_FRONT_MATTER_FAILED", "sector_card front matter is incomplete.", str(card_path)))
        try:
            front_matter_text = text.split("---", 2)[1]
            front_matter = yaml.safe_load(front_matter_text) or {}
            result = validate_output_record_shape(config, "sector_card", front_matter)
            if result.get("ok"):
                record_shape_pass_count += 1
            else:
                record_shape_fail_count += 1
                for error in result.get("errors", []):
                    findings.append(Finding("ERROR", "GENERATOR_PREVIEW_RECORD_SHAPE_FAILED", error, str(card_path)))
            if front_matter.get("source_ids") and front_matter.get("evidence_ids"):
                source_evidence_field_pass_count += 1
        except Exception as exc:  # noqa: BLE001
            record_shape_fail_count += 1
            findings.append(Finding("ERROR", "GENERATOR_PREVIEW_FRONT_MATTER_PARSE_FAILED", str(exc), str(card_path)))
        for forbidden in ("建仓评级", "买入评级", "正式投资结论"):
            if forbidden in text:
                investment_conclusion_violation_count += 1
                findings.append(Finding("ERROR", "INVESTMENT_CONCLUSION_VIOLATION", f"sector_card contains forbidden phrase {forbidden}.", str(card_path)))

    return {
        "preview_file_count": preview_file_count,
        "record_shape_pass_count": record_shape_pass_count,
        "record_shape_fail_count": record_shape_fail_count,
        "csv_header_pass_count": csv_header_pass_count,
        "markdown_front_matter_pass_count": markdown_front_matter_pass_count,
        "source_evidence_field_pass_count": source_evidence_field_pass_count,
        "canonical_missing_conflict_log_pass_count": canonical_missing_conflict_log_pass_count,
        "preview_score_table_pass_count": preview_score_table_pass_count,
        "investment_conclusion_violation_count": investment_conclusion_violation_count,
    }


def _audit_formal_output_violation(config: Any, findings: list[Finding]) -> int:
    count = 0
    if not config.output_root.exists():
        return 0
    for path in config.output_root.rglob("preview_*"):
        count += 1
        findings.append(Finding("ERROR", "GENERATOR_PREVIEW_IN_FORMAL_OUTPUT_ROOT", f"Preview file found in formal output root: {path}", str(path)))
    return count


def audit_project(project_id: str, write_report: bool = True) -> tuple[list[Finding], dict[str, Any]]:
    config = load_project(project_id, create_dirs=False, strict=False, silent=True)
    findings: list[Finding] = []
    output_types = list_output_types(config)
    expected_records = build_generator_preview_records(config, "cpo_optical_module_silicon_photonics")

    missing_types = [output_type for output_type in output_types if output_type not in expected_records]
    for output_type in missing_types:
        findings.append(Finding("ERROR", "GENERATOR_PREVIEW_TYPE_NOT_BUILDABLE", f"Adapter cannot build {output_type}."))

    file_counts = _audit_preview_files(config, findings)
    formal_violation_count = _audit_formal_output_violation(config, findings)

    if (
        not findings
        and file_counts["record_shape_pass_count"] == len(output_types)
        and file_counts["markdown_front_matter_pass_count"] == 1
    ):
        findings.append(Finding("INFO", "GENERATOR_PREVIEWS_READY", "Generator previews cover all output types and pass contract validation."))

    counts = _counts(findings)
    summary = {
        **counts,
        "output_type_count": len(output_types),
        "preview_file_count": file_counts["preview_file_count"],
        "record_shape_pass_count": file_counts["record_shape_pass_count"],
        "record_shape_fail_count": file_counts["record_shape_fail_count"],
        "csv_header_pass_count": file_counts["csv_header_pass_count"],
        "markdown_front_matter_pass_count": file_counts["markdown_front_matter_pass_count"],
        "source_evidence_field_pass_count": file_counts["source_evidence_field_pass_count"],
        "canonical_missing_conflict_log_pass_count": file_counts["canonical_missing_conflict_log_pass_count"],
        "preview_score_table_pass_count": file_counts["preview_score_table_pass_count"],
        "formal_output_write_violation_count": formal_violation_count,
        "investment_conclusion_violation_count": file_counts["investment_conclusion_violation_count"],
        "preview_output_dir": str(get_generator_preview_dir(config)),
    }

    if write_report:
        _write_report(project_id, findings, summary)
    return findings, summary


def _write_report(project_id: str, findings: list[Finding], summary: dict[str, Any]) -> None:
    audit_dir = WORKSPACE_ROOT / "investment_system" / "research" / "projects" / project_id / "audits"
    audit_dir.mkdir(parents=True, exist_ok=True)
    path = audit_dir / "generator_preview_audit.md"
    lines = [
        "# Generator Preview Audit",
        "",
        "Scope: engineering generator preview audit only. No formal research output is generated.",
        "",
        "## Summary",
    ]
    for key in [
        "ERROR", "WARNING", "INFO", "output_type_count", "preview_file_count",
        "record_shape_pass_count", "record_shape_fail_count", "csv_header_pass_count",
        "markdown_front_matter_pass_count", "source_evidence_field_pass_count",
        "canonical_missing_conflict_log_pass_count", "preview_score_table_pass_count",
        "formal_output_write_violation_count", "investment_conclusion_violation_count",
        "preview_output_dir",
    ]:
        lines.append(f"- {key}: {summary.get(key)}")
    lines.extend(["", "## Findings"])
    for finding in findings:
        loc = f" (`{finding.file}`)" if finding.file else ""
        lines.append(f"- {finding.severity} [{finding.code}]{loc}: {finding.message}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _print_summary(findings: list[Finding], summary: dict[str, Any]) -> None:
    print("Generator Preview Audit")
    print("=" * 60)
    for key in [
        "ERROR", "WARNING", "INFO", "output_type_count", "preview_file_count",
        "record_shape_pass_count", "record_shape_fail_count", "csv_header_pass_count",
        "markdown_front_matter_pass_count", "source_evidence_field_pass_count",
        "canonical_missing_conflict_log_pass_count", "preview_score_table_pass_count",
        "formal_output_write_violation_count", "investment_conclusion_violation_count",
    ]:
        print(f"{key:45}: {summary.get(key)}")
    if findings:
        print()
        print("Findings")
        for finding in findings:
            loc = f" ({finding.file})" if finding.file else ""
            print(f"  [{finding.severity}] {finding.code}{loc}: {finding.message}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit project-aware generator preview outputs.")
    parser.add_argument("--project", required=True)
    args = parser.parse_args(argv)
    findings, summary = audit_project(args.project, write_report=True)
    _print_summary(findings, summary)
    return 1 if summary["ERROR"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
