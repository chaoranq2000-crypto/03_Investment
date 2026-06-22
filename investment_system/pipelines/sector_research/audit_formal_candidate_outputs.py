"""Audit isolated formal-candidate outputs for one project-aware sector."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from investment_system.pipelines.sector_research.audit_evidence_coverage import check_sector_coverage
from investment_system.pipelines.sector_research.build_formal_candidate_outputs import (
    CANDIDATE_STATUS,
    NO_ADVICE,
    NOT_RATED,
    build_formal_candidate_records,
    get_candidate_paths,
    get_formal_candidate_output_dir,
    load_sector_evidence,
    validate_candidate_record_shapes,
)
from investment_system.pipelines.sector_research.load_project import (
    WORKSPACE_ROOT,
    get_sector,
    load_project,
)


@dataclass
class Finding:
    severity: str
    code: str
    message: str
    file: str = ""


FORBIDDEN_INVESTMENT_PATTERNS = [
    (re.compile(r"建议买入|买入建议|买入评级"), "BUY_RECOMMENDATION"),
    (re.compile(r"建议卖出|卖出建议|卖出评级"), "SELL_RECOMMENDATION"),
    (re.compile(r"建议加仓|加仓建议"), "ADD_POSITION_RECOMMENDATION"),
    (re.compile(r"建议减仓|减仓建议"), "REDUCE_POSITION_RECOMMENDATION"),
    (re.compile(r"建议建仓|建仓建议"), "BUILD_POSITION_RECOMMENDATION"),
    (re.compile(r"action_rating:\s*[ABCDE](\s|$)"), "FORMAL_ABCDE_RATING"),
    (re.compile(r"suggested_action:\s*(买入|卖出|加仓|减仓|建仓)"), "FORMAL_ACTION_FIELD"),
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _counts(findings: list[Finding]) -> dict[str, int]:
    return {
        "ERROR": sum(1 for f in findings if f.severity == "ERROR"),
        "WARNING": sum(1 for f in findings if f.severity == "WARNING"),
        "INFO": sum(1 for f in findings if f.severity == "INFO"),
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _split_ids(value: Any) -> set[str]:
    if not value:
        return set()
    if isinstance(value, list):
        return {str(v).strip() for v in value if str(v).strip()}
    return {part.strip() for part in str(value).split(",") if part.strip()}


def _candidate_files(project_id: str, sector_id: str) -> dict[str, Path]:
    config = load_project(project_id, create_dirs=False, strict=False, silent=True)
    paths = get_candidate_paths(config, sector_id)
    return {
        "sector_card": paths.sector_card,
        "company_table": paths.company_table,
        "sector_comparison_table": paths.sector_comparison_table,
        "source_index": paths.source_index,
        "missing_data_log": paths.missing_data_log,
        "conflict_data_log": paths.conflict_data_log,
        "score_table": paths.score_table,
        "metadata": paths.metadata,
    }


def _run_module(module: str, *args: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=str(WORKSPACE_ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _parse_readiness(text: str) -> dict[str, int | None]:
    result: dict[str, int | None] = {"BLOCKER": None, "HIGH": None, "MEDIUM": None, "LOW": None}
    for key in result:
        match = re.search(rf"{key}\s*:\s*(\d+)", text)
        if match:
            result[key] = int(match.group(1))
    return result


def audit_project(project_id: str, sector_id: str, write_report: bool = True) -> tuple[list[Finding], dict[str, Any]]:
    config = load_project(project_id, create_dirs=False, strict=False, silent=True)
    findings: list[Finding] = []
    paths = _candidate_files(project_id, sector_id)
    candidate_dir = get_formal_candidate_output_dir(config).resolve()
    formal_root = config.output_root.resolve()
    legacy_root = (WORKSPACE_ROOT / "科技主线调研输出").resolve()

    load_errors = [w for w in config.warnings if w.severity == "error"]
    load_warnings = [w for w in config.warnings if w.severity == "warning"]
    if load_errors:
        findings.append(Finding("ERROR", "LOAD_PROJECT_HAS_ERRORS", f"load_project errors={len(load_errors)}"))
    elif load_warnings:
        findings.append(Finding("WARNING", "LOAD_PROJECT_WARNING_ONLY", f"load_project warning-only count={len(load_warnings)}; expected exit code=3"))
    else:
        findings.append(Finding("INFO", "LOAD_PROJECT_OK", "load_project has no warnings/errors."))

    load_exit_code, _load_output = _run_module(
        "investment_system.pipelines.sector_research.load_project",
        "--project",
        project_id,
        "--json",
    )
    readiness_exit_code, readiness_output = _run_module(
        "investment_system.pipelines.sector_research.audit_pipeline_readiness",
        "--project",
        project_id,
    )
    readiness_counts = _parse_readiness(readiness_output)
    if readiness_exit_code != 0:
        findings.append(Finding("ERROR", "READINESS_COMMAND_FAILED", f"audit_pipeline_readiness exit_code={readiness_exit_code}"))
    elif readiness_counts.get("BLOCKER") != 0 or readiness_counts.get("HIGH") != 0:
        findings.append(Finding("ERROR", "READINESS_GATE_NOT_PASSED", f"readiness={readiness_counts}"))
    else:
        findings.append(Finding("INFO", "READINESS_GATE_PASSED", f"readiness={readiness_counts}"))

    try:
        sector = get_sector(config, sector_id)
        coverage = check_sector_coverage(config, sector)
        if coverage.get("coverage_status") != "ok":
            findings.append(Finding("ERROR", "TARGET_SECTOR_COVERAGE_NOT_OK", f"{sector_id} coverage={coverage.get('coverage_status')}: {coverage.get('blocking_reason')}"))
        else:
            findings.append(Finding("INFO", "TARGET_SECTOR_COVERAGE_OK", f"{sector_id} coverage OK."))
    except Exception as exc:
        findings.append(Finding("ERROR", "TARGET_SECTOR_COVERAGE_CHECK_FAILED", str(exc)))
        coverage = {}

    p0p1_counts = {"ok": 0, "partial": 0, "missing": 0}
    for row in config.raw.get("sectors", []) or []:
        if row.get("priority") not in {"P0", "P1"}:
            continue
        status = check_sector_coverage(config, row).get("coverage_status")
        if status in p0p1_counts:
            p0p1_counts[status] += 1

    for output_type, path in paths.items():
        if not path.exists():
            findings.append(Finding("ERROR", "FORMAL_CANDIDATE_FILE_MISSING", f"Missing {output_type} file.", str(path)))
            continue
        resolved = path.resolve()
        if not str(resolved).startswith(str(candidate_dir)):
            findings.append(Finding("ERROR", "FILE_OUTSIDE_CANDIDATE_DIR", f"{output_type} outside formal_candidate_outputs.", str(path)))
        if str(resolved).startswith(str(formal_root)) or str(resolved).startswith(str(legacy_root)):
            findings.append(Finding("ERROR", "FILE_IN_FORMAL_OUTPUT_ROOT", f"{output_type} in formal output root.", str(path)))

    if formal_root.exists():
        for path in formal_root.rglob("formal_candidate_*"):
            findings.append(Finding("ERROR", "FORMAL_CANDIDATE_POLLUTION", "formal_candidate file found in formal output root.", str(path)))

    records = build_formal_candidate_records(config, sector_id)
    shape = validate_candidate_record_shapes(config, records)
    shape_errors = sum(len(v["errors"]) for v in shape.values())
    shape_warnings = sum(len(v["warnings"]) for v in shape.values())
    if shape_errors:
        findings.append(Finding("ERROR", "OUTPUT_CONTRACT_SHAPE_FAILED", f"shape_errors={shape_errors}"))
    else:
        findings.append(Finding("INFO", "OUTPUT_CONTRACT_SHAPE_OK", f"shape_warnings={shape_warnings}"))

    evidence = load_sector_evidence(config, sector_id)
    evidence_ids = {str(item.get("evidence_id", "")) for item in evidence["evidence_items"] if item.get("evidence_id")}
    source_ids = set(evidence["sources_by_id"])
    used_source_ids = set(evidence["used_source_ids"])
    if not evidence["files"]:
        findings.append(Finding("ERROR", "EVIDENCE_FILES_NOT_RESOLVED", "No active evidence files resolved."))
    else:
        findings.append(Finding("INFO", "EVIDENCE_FILES_RESOLVED", f"files={len(evidence['files'])}, sources={len(source_ids)}, evidence_items={len(evidence_ids)}"))

    source_rows = _read_csv(paths["source_index"]) if paths["source_index"].exists() else []
    output_source_ids = {row.get("source_id", "") for row in source_rows if row.get("source_id")}
    if not output_source_ids:
        findings.append(Finding("ERROR", "SOURCE_INDEX_EMPTY", "source_index has no source_id rows.", str(paths["source_index"])))
    missing_sources = used_source_ids - output_source_ids
    if missing_sources:
        findings.append(Finding("ERROR", "SOURCE_ID_NOT_CLOSED", f"source_ids missing from candidate source_index: {sorted(missing_sources)}"))
    extra_sources = output_source_ids - source_ids
    if extra_sources:
        findings.append(Finding("ERROR", "SOURCE_ID_NOT_IN_EVIDENCE", f"candidate source_index includes unknown source_ids: {sorted(extra_sources)}"))

    referenced_evidence_ids: set[str] = set()
    for output_type in ["company_table", "sector_comparison_table", "source_index", "missing_data_log", "conflict_data_log", "score_table"]:
        path = paths[output_type]
        if not path.exists():
            continue
        for row in _read_csv(path):
            referenced_evidence_ids.update(_split_ids(row.get("evidence_ids") or row.get("evidence_id")))
            row_sources = _split_ids(row.get("source_ids") or row.get("source_id"))
            unknown = row_sources - output_source_ids
            if unknown:
                findings.append(Finding("ERROR", "ROW_SOURCE_ID_NOT_IN_SOURCE_INDEX", f"{output_type} row references unknown source_ids: {sorted(unknown)}", str(path)))
    unknown_evidence = referenced_evidence_ids - evidence_ids
    if unknown_evidence:
        findings.append(Finding("ERROR", "EVIDENCE_ID_NOT_IN_ACTIVE_EVIDENCE", f"Unknown evidence_ids: {sorted(unknown_evidence)}"))
    else:
        findings.append(Finding("INFO", "SOURCE_EVIDENCE_CLOSURE_OK", f"source_ids={len(output_source_ids)}, evidence_ids={len(referenced_evidence_ids)}"))

    for output_type, path in paths.items():
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8-sig", errors="ignore")
        for pattern, code in FORBIDDEN_INVESTMENT_PATTERNS:
            if pattern.search(content):
                findings.append(Finding("ERROR", f"FORMAL_INVESTMENT_LANGUAGE_{code}", f"Forbidden investment wording matched: {pattern.pattern}", str(path)))
        if output_type == "sector_card":
            required_markers = [project_id, sector_id, CANDIDATE_STATUS, NO_ADVICE, NOT_RATED]
            for marker in required_markers:
                if marker not in content:
                    findings.append(Finding("ERROR", "SECTOR_CARD_REQUIRED_MARKER_MISSING", f"Missing marker: {marker}", str(path)))

    if paths["missing_data_log"].exists() and _read_csv(paths["missing_data_log"]):
        findings.append(Finding("INFO", "MISSING_DATA_LOG_PRESENT", "missing_data_log exists with rows.", str(paths["missing_data_log"])))
    else:
        findings.append(Finding("ERROR", "MISSING_DATA_LOG_MISSING_OR_EMPTY", "missing_data_log is missing or empty.", str(paths["missing_data_log"])))
    if paths["conflict_data_log"].exists() and _read_csv(paths["conflict_data_log"]):
        findings.append(Finding("INFO", "CONFLICT_DATA_LOG_PRESENT", "conflict_data_log exists with rows.", str(paths["conflict_data_log"])))
    else:
        findings.append(Finding("ERROR", "CONFLICT_DATA_LOG_MISSING_OR_EMPTY", "conflict_data_log is missing or empty.", str(paths["conflict_data_log"])))

    if not any(f.code in {"FILE_IN_FORMAL_OUTPUT_ROOT", "FORMAL_CANDIDATE_POLLUTION"} for f in findings):
        findings.append(Finding("INFO", "FORMAL_DIRECTORY_POLLUTION_OK", "No formal_candidate files found in formal output root."))
    if not any(f.code.startswith("FORMAL_INVESTMENT_LANGUAGE") for f in findings):
        findings.append(Finding("INFO", "NO_INVESTMENT_CONCLUSION_OK", "No forbidden buy/sell/add/reduce/build-position wording found."))

    counts = _counts(findings)
    summary = {
        **counts,
        "project_id": project_id,
        "sector_id": sector_id,
        "audit_time": _now_iso(),
        "output_dir": str(candidate_dir),
        "generated_files": {k: str(v) for k, v in paths.items()},
        "load_project_warning_count": len(load_warnings),
        "load_project_error_count": len(load_errors),
        "load_project_actual_exit_code": load_exit_code,
        "load_project_expected_warning_exit_code": 3 if load_warnings and not load_errors else 0,
        "readiness_exit_code": readiness_exit_code,
        "readiness_counts": readiness_counts,
        "coverage_status": coverage.get("coverage_status"),
        "p0p1_coverage_counts": p0p1_counts,
        "evidence_file_count": len(evidence["files"]),
        "source_count": len(source_ids),
        "evidence_item_count": len(evidence_ids),
        "source_id_closure": not any(f.code in {"SOURCE_ID_NOT_CLOSED", "SOURCE_ID_NOT_IN_EVIDENCE", "ROW_SOURCE_ID_NOT_IN_SOURCE_INDEX"} for f in findings),
        "evidence_id_closure": not any(f.code == "EVIDENCE_ID_NOT_IN_ACTIVE_EVIDENCE" for f in findings),
        "shape_errors": shape_errors,
        "shape_warnings": shape_warnings,
        "recommend_next_stage": counts["ERROR"] == 0,
    }

    if write_report:
        _write_report(findings, summary)

    return findings, summary


def _write_report(findings: list[Finding], summary: dict[str, Any]) -> None:
    audit_dir = WORKSPACE_ROOT / "investment_system" / "research" / "projects" / summary["project_id"] / "audits"
    audit_dir.mkdir(parents=True, exist_ok=True)
    path = audit_dir / "formal_candidate_output_audit.md"
    lines = [
        "# Formal Candidate Output Audit",
        "",
        f"- audit_time: {summary['audit_time']}",
        f"- project_id: `{summary['project_id']}`",
        f"- sector_id: `{summary['sector_id']}`",
        f"- output_dir: `{summary['output_dir']}`",
        "",
        "## 前置门禁结果",
        f"- load_project: actual_exit_code={summary['load_project_actual_exit_code']}, warning_count={summary['load_project_warning_count']}, error_count={summary['load_project_error_count']}, expected_warning_exit_code={summary['load_project_expected_warning_exit_code']}",
        f"- readiness: exit_code={summary['readiness_exit_code']}, counts={summary['readiness_counts']}",
        f"- evidence coverage: {summary.get('coverage_status')}",
        f"- P0/P1 coverage counts: {summary['p0p1_coverage_counts']}",
        "",
        "## 生成文件清单",
    ]
    for name, file_path in summary["generated_files"].items():
        lines.append(f"- {name}: `{file_path}`")
    lines.extend([
        "",
        "## Evidence 解析结果",
        f"- evidence_file_count: {summary['evidence_file_count']}",
        f"- source_count: {summary['source_count']}",
        f"- evidence_item_count: {summary['evidence_item_count']}",
        f"- source_id_closure: {summary['source_id_closure']}",
        f"- evidence_id_closure: {summary['evidence_id_closure']}",
        "",
        "## 质量门禁结果",
        f"- no_investment_conclusion: {not any(f.code.startswith('FORMAL_INVESTMENT_LANGUAGE') for f in findings)}",
        f"- formal_directory_pollution: {not any(f.code in {'FILE_IN_FORMAL_OUTPUT_ROOT', 'FORMAL_CANDIDATE_POLLUTION'} for f in findings)}",
        f"- output_spec_schema_alignment: shape_errors={summary['shape_errors']}, shape_warnings={summary['shape_warnings']}",
        f"- missing_conflict_logs: {'ok' if any(f.code == 'MISSING_DATA_LOG_PRESENT' for f in findings) and any(f.code == 'CONFLICT_DATA_LOG_PRESENT' for f in findings) else 'failed'}",
        "",
        "## ERROR/WARNING/INFO 汇总",
        f"- ERROR: {summary['ERROR']}",
        f"- WARNING: {summary['WARNING']}",
        f"- INFO: {summary['INFO']}",
        f"- recommend_next_stage: {summary['recommend_next_stage']}",
        "",
        "## Findings",
    ])
    for severity in ["ERROR", "WARNING", "INFO"]:
        rows = [f for f in findings if f.severity == severity]
        if not rows:
            continue
        lines.append(f"\n### {severity}\n")
        for finding in rows:
            loc = f" (`{finding.file}`)" if finding.file else ""
            lines.append(f"- `{finding.code}`{loc}: {finding.message}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _print_summary(summary: dict[str, Any]) -> None:
    print("Formal Candidate Output Audit")
    print("=" * 60)
    print(f"project_id: {summary['project_id']}")
    print(f"sector_id: {summary['sector_id']}")
    print(f"output_dir: {summary['output_dir']}")
    print(f"ERROR: {summary['ERROR']}")
    print(f"WARNING: {summary['WARNING']}")
    print(f"INFO: {summary['INFO']}")
    print(f"coverage_status: {summary.get('coverage_status')}")
    print(f"evidence_file_count: {summary['evidence_file_count']}")
    print(f"source_id_closure: {summary['source_id_closure']}")
    print(f"evidence_id_closure: {summary['evidence_id_closure']}")
    print(f"shape_errors: {summary['shape_errors']}")
    print(f"shape_warnings: {summary['shape_warnings']}")
    print(f"recommend_next_stage: {summary['recommend_next_stage']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit isolated formal-candidate outputs.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--sector-id", required=True)
    args = parser.parse_args(argv)

    findings, summary = audit_project(args.project, args.sector_id, write_report=True)
    _print_summary(summary)
    if summary["ERROR"]:
        print("Errors:")
        for finding in findings:
            if finding.severity == "ERROR":
                print(f"  [{finding.code}] {finding.message} {finding.file}")
    return 1 if summary["ERROR"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
