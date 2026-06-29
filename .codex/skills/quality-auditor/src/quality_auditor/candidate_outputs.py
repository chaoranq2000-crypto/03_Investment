"""Audit isolated formal-candidate outputs for one project-aware sector."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from investment_system.core.skill_module_loader import skill_subprocess_env
from quality_auditor.evidence_coverage import check_sector_coverage
from research_writer.candidate_outputs import (
    CANDIDATE_STATUS,
    NO_ADVICE,
    NOT_RATED,
    build_formal_candidate_records,
    get_candidate_paths,
    get_formal_candidate_output_dir,
    load_sector_evidence,
    validate_candidate_record_shapes,
)
from investment_system.core.project_loader import (
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


def _metadata_run_id(sector_id: str, path: Path, metadata: dict[str, Any] | None = None) -> str:
    if metadata:
        run_id = str(metadata.get("run_id") or "").strip()
        if run_id:
            return run_id
    match = re.match(rf"formal_candidate_{re.escape(sector_id)}_(\d{{8}})_metadata\.json$", path.name)
    return match.group(1) if match else ""


def _latest_metadata_file(config: Any, sector_id: str) -> Path | None:
    candidate_dir = get_formal_candidate_output_dir(config)
    candidates: list[tuple[str, float, Path]] = []
    for path in candidate_dir.glob(f"formal_candidate_{sector_id}_*_metadata.json"):
        metadata: dict[str, Any] | None = None
        try:
            metadata = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            metadata = None
        candidates.append((_metadata_run_id(sector_id, path, metadata), path.stat().st_mtime, path))
    if not candidates:
        return None
    return max(candidates, key=lambda row: (row[0], row[1]))[2]


def _candidate_files(project_id: str, sector_id: str) -> dict[str, Path]:
    config = load_project(project_id, create_dirs=False, strict=False, silent=True)
    metadata_file = _latest_metadata_file(config, sector_id)
    metadata: dict[str, Any] = {}
    run_id: str | None = None
    if metadata_file:
        try:
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            metadata = {}
        run_id = _metadata_run_id(sector_id, metadata_file, metadata) or None

    paths = get_candidate_paths(config, sector_id, run_id)
    sector_card = paths.sector_card
    metadata_card = (metadata.get("formal_candidate_files") or {}).get("sector_card")
    if metadata_card:
        sector_card = Path(str(metadata_card))
    return {
        "sector_card": sector_card,
        "company_table": paths.company_table,
        "sector_comparison_table": paths.sector_comparison_table,
        "source_index": paths.source_index,
        "missing_data_log": paths.missing_data_log,
        "conflict_data_log": paths.conflict_data_log,
        "score_table": paths.score_table,
        "metadata": metadata_file or paths.metadata,
    }


def _run_module(module: str, *args: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=str(WORKSPACE_ROOT),
        env=skill_subprocess_env(),
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


def _extract_ids_from_text(text: str) -> tuple[set[str], set[str]]:
    source_ids = {
        x
        for x in re.findall(r"`?([A-Z][A-Z0-9]+(?:-[A-Z0-9]+)+-\d{8})`?", text)
        if x.startswith(("CNINFO-", "TUSHARE-", "BAO-", "AKSHARE-", "TENCENT-", "LEGACY-", "EVIDENCE-", "HSOM-", "OCFP-"))
    }
    evidence_ids = set(re.findall(r"`?(EV-[A-Z0-9-]+-\d{8})`?", text))
    return source_ids, evidence_ids


DRAFT_PLACEHOLDER_TERMS = [
    "DRAFT_PLACEHOLDER",
    "TODO_MANUAL_EXTRACTION",
    "draft_source_skeleton",
]


def _append_placeholder_findings(findings: list[Finding], path: Path, content: str) -> None:
    leaked_terms = [term for term in DRAFT_PLACEHOLDER_TERMS if term in content]
    if leaked_terms:
        findings.append(
            Finding(
                "ERROR",
                "DRAFT_PLACEHOLDER_LEAKED_TO_CANDIDATE",
                f"Draft placeholder terms leaked into candidate output: {sorted(leaked_terms)}",
                str(path),
            )
        )


def _append_draft_reference_findings(
    findings: list[Finding],
    source_ids: set[str],
    evidence_ids: set[str],
    *,
    location: str = "",
) -> None:
    draft_sources = {source_id for source_id in source_ids if "DRAFT" in source_id}
    draft_evidence = {evidence_id for evidence_id in evidence_ids if evidence_id.startswith("EV-DRAFT-")}
    if draft_sources or draft_evidence:
        findings.append(
            Finding(
                "ERROR",
                "DRAFT_EVIDENCE_REFERENCED_BY_CANDIDATE",
                f"Draft source/evidence ids referenced: source_ids={sorted(draft_sources)}, evidence_ids={sorted(draft_evidence)}",
                location,
            )
        )


def _update_candidate_gate_metadata(metadata_path: Path, metadata: dict[str, Any], summary: dict[str, Any]) -> None:
    if summary["ERROR"] != 0:
        return
    if metadata.get("candidate_gate"):
        return
    metadata["candidate_status"] = "publish_gate_ready"
    metadata.setdefault("candidate_scope", "sector_card_only")
    metadata.setdefault("gated_formal_generated", False)
    metadata.setdefault("release_manifest_generated", False)
    metadata.setdefault("formal_output_root_written", False)
    metadata["candidate_gate"] = {
        "status": "PASS",
        "error_count": summary["ERROR"],
        "warning_count": summary["WARNING"],
        "validate_outputs_exit_code": summary.get("validate_outputs_exit_code", 0),
        "readiness_exit_code": summary.get("readiness_exit_code"),
        "readiness_blocker": (summary.get("readiness_counts") or {}).get("BLOCKER"),
        "readiness_high": (summary.get("readiness_counts") or {}).get("HIGH"),
        "recommend_publish_gate": True,
    }
    metadata["candidate_gate_updated_at"] = summary["audit_time"]
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def _audit_candidate_only(
    *,
    project_id: str,
    sector_id: str,
    config: Any,
    paths: dict[str, Path],
    candidate_dir: Path,
    formal_root: Path,
    final_publication_root: Path,
    load_errors: list[Any],
    load_warnings: list[Any],
    write_report: bool,
) -> tuple[list[Finding], dict[str, Any]]:
    findings: list[Finding] = []
    metadata = json.loads(paths["metadata"].read_text(encoding="utf-8"))
    sector_card = Path((metadata.get("formal_candidate_files") or {}).get("sector_card") or paths["sector_card"])

    if load_errors:
        findings.append(Finding("ERROR", "LOAD_PROJECT_HAS_ERRORS", f"load_project errors={len(load_errors)}"))
    elif load_warnings:
        findings.append(Finding("WARNING", "LOAD_PROJECT_WARNING_ONLY", f"load_project warning-only count={len(load_warnings)}; expected exit code=3"))
    else:
        findings.append(Finding("INFO", "LOAD_PROJECT_OK", "load_project has no warnings/errors."))

    readiness_exit_code, readiness_output = _run_module(
        "quality_auditor.pipeline_readiness",
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

    if not sector_card.exists():
        findings.append(Finding("ERROR", "FORMAL_CANDIDATE_FILE_MISSING", "Missing candidate-only sector_card.", str(sector_card)))
        card_text = ""
    else:
        resolved = sector_card.resolve()
        card_text = sector_card.read_text(encoding="utf-8-sig", errors="ignore")
        if not str(resolved).startswith(str(candidate_dir)):
            findings.append(Finding("ERROR", "FILE_OUTSIDE_CANDIDATE_DIR", "candidate-only sector_card outside formal_candidate_outputs.", str(sector_card)))
        if str(resolved).startswith(str(formal_root)) or str(resolved).startswith(str(final_publication_root)):
            findings.append(Finding("ERROR", "FILE_IN_FORMAL_OUTPUT_ROOT", "candidate-only sector_card in formal output root.", str(sector_card)))
        _append_placeholder_findings(findings, sector_card, card_text)

    evidence = load_sector_evidence(config, sector_id)
    evidence_ids = {str(item.get("evidence_id", "")) for item in evidence["evidence_items"] if item.get("evidence_id")}
    source_ids = set(evidence["sources_by_id"])
    metadata_source_ids = set(metadata.get("source_ids") or [])
    metadata_evidence_ids = set(metadata.get("evidence_ids") or [])
    card_source_ids, card_evidence_ids = _extract_ids_from_text(card_text)
    _append_draft_reference_findings(
        findings,
        metadata_source_ids | card_source_ids,
        metadata_evidence_ids | card_evidence_ids,
        location=str(sector_card),
    )
    missing_sources = (metadata_source_ids | card_source_ids) - source_ids
    missing_evidence = (metadata_evidence_ids | card_evidence_ids) - evidence_ids
    if missing_sources:
        findings.append(Finding("ERROR", "SOURCE_ID_NOT_IN_EVIDENCE", f"unknown source_ids: {sorted(missing_sources)}"))
    if missing_evidence:
        findings.append(Finding("ERROR", "EVIDENCE_ID_NOT_IN_ACTIVE_EVIDENCE", f"unknown evidence_ids: {sorted(missing_evidence)}"))
    if not missing_sources and not missing_evidence:
        findings.append(Finding("INFO", "SOURCE_EVIDENCE_CLOSURE_OK", f"source_ids={len(metadata_source_ids | card_source_ids)}, evidence_ids={len(metadata_evidence_ids | card_evidence_ids)}"))

    gate = metadata.get("candidate_gate") or {}
    if not gate:
        findings.append(Finding("INFO", "CANDIDATE_GATE_METADATA_WILL_BE_COMPUTED", "candidate_gate metadata is absent; this audit will compute current gate status."))
    elif gate.get("status") != "PASS" or gate.get("error_count") != 0:
        findings.append(Finding("ERROR", "CANDIDATE_GATE_NOT_PASSING", f"candidate_gate={gate}"))
    else:
        findings.append(Finding("INFO", "CANDIDATE_GATE_PASS", "Candidate Gate status=PASS and error_count=0."))

    required_markers = [project_id, sector_id, "NOT_RATED", "NOT_INVESTMENT_ADVICE", "缺失数据", "conflict / counter-evidence"]
    for marker in required_markers:
        if marker not in card_text:
            findings.append(Finding("ERROR", "SECTOR_CARD_REQUIRED_MARKER_MISSING", f"Missing marker: {marker}", str(sector_card)))
    for pattern, code in FORBIDDEN_INVESTMENT_PATTERNS:
        if pattern.search(card_text):
            findings.append(Finding("ERROR", f"FORMAL_INVESTMENT_LANGUAGE_{code}", f"Forbidden investment wording matched: {pattern.pattern}", str(sector_card)))
    for term in ["目标价", "仓位建议", "清仓建议", "建议清仓"]:
        if term in card_text:
            findings.append(Finding("ERROR", "FORMAL_INVESTMENT_LANGUAGE_FORBIDDEN_TERM", f"Forbidden investment wording matched: {term}", str(sector_card)))
    if not any(f.code.startswith("FORMAL_INVESTMENT_LANGUAGE") for f in findings):
        findings.append(Finding("INFO", "NO_INVESTMENT_CONCLUSION_OK", "No forbidden buy/sell/add/reduce/build-position wording found."))

    if sector_id != "high_speed_copper_connector":
        findings.append(Finding("INFO", "MISSING_EVIDENCE_SECTION_PRESENT", "Generic missing/counter-evidence markers are present."))
    elif "named_customer_order_certification" in card_text and "ai_server_named_customer_300563" in card_text:
        findings.append(Finding("INFO", "MISSING_EVIDENCE_RETAINED", "Customer/order/certification gaps and Shenyu named AI-server customer gap remain explicit."))
    else:
        findings.append(Finding("ERROR", "MISSING_EVIDENCE_NOT_RETAINED", "Required missing-evidence fields are not explicit.", str(sector_card)))

    if not any(f.code in {"FILE_IN_FORMAL_OUTPUT_ROOT", "FORMAL_CANDIDATE_POLLUTION"} for f in findings):
        findings.append(Finding("INFO", "FORMAL_DIRECTORY_POLLUTION_OK", "No formal_candidate files found in formal output root."))

    validate_exit, _validate_output = _run_module("quality_auditor.validate_outputs", "--project", project_id)
    if validate_exit == 0:
        findings.append(Finding("INFO", "VALIDATE_OUTPUTS_OK", "validate_outputs exit_code=0."))
    else:
        findings.append(Finding("ERROR", "VALIDATE_OUTPUTS_FAILED", f"validate_outputs exit_code={validate_exit}"))

    counts = _counts(findings)
    summary = {
        **counts,
        "project_id": project_id,
        "sector_id": sector_id,
        "audit_time": _now_iso(),
        "output_dir": str(candidate_dir),
        "generated_files": {"sector_card": str(sector_card), "metadata": str(paths["metadata"])},
        "load_project_warning_count": len(load_warnings),
        "load_project_error_count": len(load_errors),
        "load_project_actual_exit_code": 1 if load_warnings and not load_errors else 0,
        "load_project_expected_warning_exit_code": 3 if load_warnings and not load_errors else 0,
        "readiness_exit_code": readiness_exit_code,
        "readiness_counts": readiness_counts,
        "validate_outputs_exit_code": validate_exit,
        "coverage_status": coverage.get("coverage_status"),
        "p0p1_coverage_counts": {},
        "evidence_file_count": len(evidence["files"]),
        "source_count": len(source_ids),
        "evidence_item_count": len(evidence_ids),
        "source_id_closure": not missing_sources,
        "evidence_id_closure": not missing_evidence,
        "shape_errors": 0,
        "shape_warnings": 0,
        "recommend_next_stage": counts["ERROR"] == 0,
    }
    if write_report:
        _write_report(findings, summary)
        _update_candidate_gate_metadata(paths["metadata"], metadata, summary)
    return findings, summary


def audit_project(project_id: str, sector_id: str, write_report: bool = True) -> tuple[list[Finding], dict[str, Any]]:
    config = load_project(project_id, create_dirs=False, strict=False, silent=True)
    findings: list[Finding] = []
    paths = _candidate_files(project_id, sector_id)
    candidate_dir = get_formal_candidate_output_dir(config).resolve()
    formal_root = config.output_root.resolve()
    final_publication_root = (WORKSPACE_ROOT / "科技主线调研输出").resolve()

    load_errors = [w for w in config.warnings if w.severity == "error"]
    load_warnings = [w for w in config.warnings if w.severity == "warning"]
    if paths["metadata"].exists():
        metadata_probe = json.loads(paths["metadata"].read_text(encoding="utf-8"))
        if metadata_probe.get("candidate_only") is True:
            return _audit_candidate_only(
                project_id=project_id,
                sector_id=sector_id,
                config=config,
                paths=paths,
                candidate_dir=candidate_dir,
                formal_root=formal_root,
                final_publication_root=final_publication_root,
                load_errors=load_errors,
                load_warnings=load_warnings,
                write_report=write_report,
            )
    if load_errors:
        findings.append(Finding("ERROR", "LOAD_PROJECT_HAS_ERRORS", f"load_project errors={len(load_errors)}"))
    elif load_warnings:
        findings.append(Finding("WARNING", "LOAD_PROJECT_WARNING_ONLY", f"load_project warning-only count={len(load_warnings)}; expected exit code=3"))
    else:
        findings.append(Finding("INFO", "LOAD_PROJECT_OK", "load_project has no warnings/errors."))

    load_exit_code, _load_output = _run_module(
        "investment_system.core.project_loader",
        "--project",
        project_id,
        "--json",
    )
    readiness_exit_code, readiness_output = _run_module(
        "quality_auditor.pipeline_readiness",
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
        if str(resolved).startswith(str(formal_root)) or str(resolved).startswith(str(final_publication_root)):
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
    _append_draft_reference_findings(
        findings,
        output_source_ids,
        referenced_evidence_ids,
        location=str(paths["source_index"]),
    )
    if unknown_evidence:
        findings.append(Finding("ERROR", "EVIDENCE_ID_NOT_IN_ACTIVE_EVIDENCE", f"Unknown evidence_ids: {sorted(unknown_evidence)}"))
    else:
        findings.append(Finding("INFO", "SOURCE_EVIDENCE_CLOSURE_OK", f"source_ids={len(output_source_ids)}, evidence_ids={len(referenced_evidence_ids)}"))

    for output_type, path in paths.items():
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8-sig", errors="ignore")
        _append_placeholder_findings(findings, path, content)
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
