"""Audit gated formal staging outputs before final publication."""

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
from investment_system.core.project_loader import WORKSPACE_ROOT, load_project
from sector_research_orchestrator.promote import (
    FORBIDDEN_PATTERNS,
    GATED_STATUS,
    NO_ADVICE,
    NOT_RATED,
    REQUIRED_OUTPUTS,
    get_gated_formal_output_dir,
)


@dataclass
class Finding:
    severity: str
    code: str
    message: str
    file: str = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _counts(findings: list[Finding]) -> dict[str, int]:
    return {
        "ERROR": sum(1 for f in findings if f.severity == "ERROR"),
        "WARNING": sum(1 for f in findings if f.severity == "WARNING"),
        "INFO": sum(1 for f in findings if f.severity == "INFO"),
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


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _split_ids(value: Any) -> set[str]:
    if not value:
        return set()
    return {part.strip() for part in str(value).split(",") if part.strip()}


def _latest_metadata(gated_root: Path, sector_id: str) -> Path:
    matches = sorted(gated_root.glob(f"gated_formal_{sector_id}_*_metadata.json"))
    if not matches:
        raise FileNotFoundError(f"No gated formal metadata found for {sector_id} in {gated_root}")
    return matches[-1]


def _ids_from_outputs(files: dict[str, str]) -> tuple[set[str], set[str]]:
    source_ids: set[str] = set()
    evidence_ids: set[str] = set()
    for output_type in REQUIRED_OUTPUTS:
        path = Path(files.get(output_type, ""))
        if not path.exists() or path.suffix.lower() != ".csv":
            continue
        for row in _read_csv(path):
            source_ids.update(_split_ids(row.get("source_id") or row.get("source_ids")))
            evidence_ids.update(_split_ids(row.get("evidence_id") or row.get("evidence_ids")))
    return source_ids, evidence_ids


def _audit_score_placeholder(score_path: Path, findings: list[Finding]) -> bool:
    ok = True
    rows = _read_csv(score_path) if score_path.exists() else []
    if not rows:
        findings.append(Finding("ERROR", "SCORE_TABLE_EMPTY", "score_table missing or empty.", str(score_path)))
        return False
    for row in rows:
        if row.get("rating") != NOT_RATED:
            ok = False
            findings.append(Finding("ERROR", "FORMAL_SCORE_RATING_ENABLED", "score_table rating is not NOT_RATED.", str(score_path)))
        if row.get("data_status") != "score_placeholder":
            ok = False
            findings.append(Finding("ERROR", "FORMAL_SCORE_NOT_PLACEHOLDER", "score_table data_status is not score_placeholder.", str(score_path)))
        for field in [
            "prosperity_score",
            "earnings_certainty_score",
            "valuation_score",
            "trading_comfort_score",
            "catalyst_score",
            "purity_score",
            "risk_control_score",
            "total_score",
        ]:
            if row.get(field) != "not_applicable":
                ok = False
                findings.append(Finding("ERROR", "FORMAL_SCORE_VALUE_ENABLED", f"{field} is not not_applicable.", str(score_path)))
    if ok:
        findings.append(Finding("INFO", "SCORE_PLACEHOLDER_OK", "score_table remains score_placeholder/not_applicable.", str(score_path)))
    return ok


def audit_project(project_id: str, sector_id: str, write_report: bool = True) -> tuple[list[Finding], dict[str, Any]]:
    config = load_project(project_id, create_dirs=False, strict=False, silent=True)
    findings: list[Finding] = []
    gated_root = get_gated_formal_output_dir(config)
    formal_root = config.output_root.resolve()
    legacy_root = (WORKSPACE_ROOT / "科技主线调研输出").resolve()

    try:
        metadata_path = _latest_metadata(gated_root, sector_id)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except Exception as exc:
        findings.append(Finding("ERROR", "GATED_METADATA_MISSING", str(exc)))
        metadata_path = gated_root / f"gated_formal_{sector_id}_metadata.json"
        metadata = {}

    files = metadata.get("gated_formal_files", {}) or {}
    candidate_files = metadata.get("source_candidate_files", {}) or {}

    for output_type in REQUIRED_OUTPUTS:
        raw = files.get(output_type)
        if not raw:
            findings.append(Finding("ERROR", "GATED_FILE_NOT_DECLARED", f"{output_type} missing from metadata."))
            continue
        path = Path(raw)
        if not path.exists():
            findings.append(Finding("ERROR", "GATED_FILE_MISSING", f"{output_type} file missing.", str(path)))
            continue
        resolved = path.resolve()
        name = path.name
        if "gated_formal" not in name or sector_id not in name or not re.search(r"\d{8}", name):
            findings.append(Finding("ERROR", "GATED_FILENAME_MARKER_MISSING", f"Invalid gated filename: {name}", str(path)))
        if not str(resolved).startswith(str(gated_root.resolve())):
            findings.append(Finding("ERROR", "GATED_FILE_OUTSIDE_STAGING", f"{output_type} outside gated staging.", str(path)))
        if str(resolved).startswith(str(formal_root)) or str(resolved).startswith(str(legacy_root)):
            findings.append(Finding("ERROR", "GATED_FILE_IN_FORMAL_OUTPUT_ROOT", f"{output_type} in formal output root.", str(path)))

    if metadata_path.exists():
        if str(metadata_path.resolve()).startswith(str(formal_root)) or str(metadata_path.resolve()).startswith(str(legacy_root)):
            findings.append(Finding("ERROR", "GATED_METADATA_IN_FORMAL_OUTPUT_ROOT", "metadata in formal output root.", str(metadata_path)))
        if metadata.get("action_rating") != NOT_RATED:
            findings.append(Finding("ERROR", "GATED_ACTION_RATING_INVALID", f"action_rating={metadata.get('action_rating')}", str(metadata_path)))
        if metadata.get("suggested_action") != GATED_STATUS:
            findings.append(Finding("ERROR", "GATED_SUGGESTED_ACTION_INVALID", f"suggested_action={metadata.get('suggested_action')}", str(metadata_path)))
        if metadata.get("investment_conclusion") != NO_ADVICE:
            findings.append(Finding("ERROR", "GATED_INVESTMENT_CONCLUSION_INVALID", f"investment_conclusion={metadata.get('investment_conclusion')}", str(metadata_path)))
        if not metadata.get("candidate_metadata_path") or not Path(metadata.get("candidate_metadata_path", "")).exists():
            findings.append(Finding("ERROR", "CANDIDATE_METADATA_LINK_MISSING", "candidate metadata path missing or not found.", str(metadata_path)))
        if "candidate_audit" not in metadata:
            findings.append(Finding("ERROR", "CANDIDATE_AUDIT_STATUS_MISSING", "metadata lacks candidate_audit.", str(metadata_path)))
        else:
            candidate_audit = metadata.get("candidate_audit") or {}
            if candidate_audit.get("ERROR") != 0:
                findings.append(Finding("ERROR", "CANDIDATE_AUDIT_NOT_PASSING", f"candidate audit ERROR={candidate_audit.get('ERROR')}", str(metadata_path)))
            elif not candidate_audit.get("source_id_closure") or not candidate_audit.get("evidence_id_closure"):
                findings.append(Finding("ERROR", "CANDIDATE_CLOSURE_NOT_PASSING", "candidate source/evidence closure false.", str(metadata_path)))
            else:
                findings.append(Finding("INFO", "CANDIDATE_AUDIT_PASS_RECORDED", "candidate audit pass and closure recorded.", str(metadata_path)))

    if formal_root.exists():
        for path in formal_root.rglob("gated_formal_*"):
            findings.append(Finding("ERROR", "GATED_FORMAL_POLLUTION", "gated_formal file found in final formal output root.", str(path)))

    forbidden_hits = 0
    for output_type, raw in {**files, "metadata": str(metadata_path)}.items():
        path = Path(raw)
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8-sig", errors="ignore")
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(content):
                forbidden_hits += 1
                findings.append(Finding("ERROR", "FORMAL_INVESTMENT_LANGUAGE", f"{output_type} matched {pattern.pattern}", str(path)))
        if output_type == "sector_card":
            for marker in [project_id, sector_id, GATED_STATUS, NOT_RATED, NO_ADVICE]:
                if marker not in content:
                    findings.append(Finding("ERROR", "SECTOR_CARD_MARKER_MISSING", f"sector_card missing {marker}", str(path)))

    if forbidden_hits == 0:
        findings.append(Finding("INFO", "NO_INVESTMENT_CONCLUSION_OK", "No forbidden formal investment wording found."))

    if "score_table" in files:
        _audit_score_placeholder(Path(files["score_table"]), findings)

    gated_source_ids, gated_evidence_ids = _ids_from_outputs(files)
    candidate_source_ids, candidate_evidence_ids = _ids_from_outputs(candidate_files)
    if not gated_source_ids:
        findings.append(Finding("ERROR", "GATED_SOURCE_IDS_EMPTY", "No source_ids found in gated outputs."))
    if not gated_evidence_ids:
        findings.append(Finding("ERROR", "GATED_EVIDENCE_IDS_EMPTY", "No evidence_ids found in gated outputs."))
    if candidate_source_ids and gated_source_ids != candidate_source_ids:
        findings.append(Finding("ERROR", "SOURCE_ID_CLOSURE_CHANGED", "Gated source_id set differs from candidate source_id set."))
    if candidate_evidence_ids and gated_evidence_ids != candidate_evidence_ids:
        findings.append(Finding("ERROR", "EVIDENCE_ID_CLOSURE_CHANGED", "Gated evidence_id set differs from candidate evidence_id set."))
    if gated_source_ids and gated_evidence_ids and not any(f.code in {"SOURCE_ID_CLOSURE_CHANGED", "EVIDENCE_ID_CLOSURE_CHANGED"} for f in findings):
        findings.append(Finding("INFO", "SOURCE_EVIDENCE_CLOSURE_OK", f"source_ids={len(gated_source_ids)}, evidence_ids={len(gated_evidence_ids)}"))

    if files.get("missing_data_log") and Path(files["missing_data_log"]).exists():
        findings.append(Finding("INFO", "MISSING_DATA_LOG_PRESENT", "missing_data_log present.", files["missing_data_log"]))
    else:
        findings.append(Finding("ERROR", "MISSING_DATA_LOG_MISSING", "missing_data_log missing."))
    if files.get("conflict_data_log") and Path(files["conflict_data_log"]).exists():
        findings.append(Finding("INFO", "CONFLICT_DATA_LOG_PRESENT", "conflict_data_log present.", files["conflict_data_log"]))
    else:
        findings.append(Finding("ERROR", "CONFLICT_DATA_LOG_MISSING", "conflict_data_log missing."))

    validate_exit, validate_output = _run_module("quality_auditor.validate_outputs", "--project", project_id)
    if validate_exit == 0:
        findings.append(Finding("INFO", "VALIDATE_OUTPUTS_OK", "validate_outputs completed without error."))
    else:
        findings.append(Finding("ERROR", "VALIDATE_OUTPUTS_FAILED", f"validate_outputs exit_code={validate_exit}"))

    counts = _counts(findings)
    summary = {
        **counts,
        "audit_time": _now_iso(),
        "project_id": project_id,
        "sector_id": sector_id,
        "formal_candidate_root": metadata.get("candidate_root", ""),
        "gated_formal_root": str(gated_root),
        "metadata_path": str(metadata_path),
        "generated_files": files,
        "candidate_files": candidate_files,
        "candidate_integrity": bool(candidate_files) and all(Path(v).exists() for v in candidate_files.values()),
        "source_id_closure": not any(f.code == "SOURCE_ID_CLOSURE_CHANGED" for f in findings) and bool(gated_source_ids),
        "evidence_id_closure": not any(f.code == "EVIDENCE_ID_CLOSURE_CHANGED" for f in findings) and bool(gated_evidence_ids),
        "no_investment_conclusion": forbidden_hits == 0,
        "score_placeholder": not any(f.code.startswith("FORMAL_SCORE") or f.code == "SCORE_TABLE_EMPTY" for f in findings),
        "formal_directory_pollution": not any(f.code in {"GATED_FILE_IN_FORMAL_OUTPUT_ROOT", "GATED_METADATA_IN_FORMAL_OUTPUT_ROOT", "GATED_FORMAL_POLLUTION"} for f in findings),
        "validate_outputs_exit_code": validate_exit,
        "validate_outputs_key_result": "passed" if validate_exit == 0 else "failed",
        "recommend_next_stage": counts["ERROR"] == 0,
    }
    if write_report:
        _write_report(findings, summary)
    return findings, summary


def _write_report(findings: list[Finding], summary: dict[str, Any]) -> None:
    audit_dir = WORKSPACE_ROOT / "investment_system" / "research" / "projects" / summary["project_id"] / "audits"
    audit_dir.mkdir(parents=True, exist_ok=True)
    path = audit_dir / "gated_formal_output_audit.md"
    lines = [
        "# Gated Formal Output Audit",
        "",
        f"- audit_time: {summary['audit_time']}",
        f"- project_id: `{summary['project_id']}`",
        f"- sector_id: `{summary['sector_id']}`",
        f"- formal candidate source: `{summary['formal_candidate_root']}`",
        f"- gated formal staging: `{summary['gated_formal_root']}`",
        "",
        "## 候选文件完整性检查",
        f"- candidate_integrity: {summary['candidate_integrity']}",
        f"- candidate_files: {len(summary['candidate_files'])}",
        "",
        "## formal candidate audit 复核结果",
        f"- candidate audit recorded: {'candidate_audit' in (json.loads(Path(summary['metadata_path']).read_text(encoding='utf-8')) if Path(summary['metadata_path']).exists() else {})}",
        f"- source_id_closure: {summary['source_id_closure']}",
        f"- evidence_id_closure: {summary['evidence_id_closure']}",
        "",
        "## promote 脚本执行结果",
        f"- metadata_path: `{summary['metadata_path']}`",
        f"- promoted_file_count: {len(summary['generated_files'])}",
        "",
        "## gated formal 文件清单",
    ]
    for name, file_path in summary["generated_files"].items():
        lines.append(f"- {name}: `{file_path}`")
    lines.extend([
        "",
        "## 质量门禁结果",
        f"- no_investment_conclusion: {summary['no_investment_conclusion']}",
        f"- score_placeholder_not_applicable: {summary['score_placeholder']}",
        f"- formal_directory_pollution: {summary['formal_directory_pollution']}",
        f"- validate_outputs: exit_code={summary['validate_outputs_exit_code']}, result={summary['validate_outputs_key_result']}",
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
    print("Gated Formal Output Audit")
    print("=" * 60)
    print(f"project_id: {summary['project_id']}")
    print(f"sector_id: {summary['sector_id']}")
    print(f"gated_formal_root: {summary['gated_formal_root']}")
    print(f"ERROR: {summary['ERROR']}")
    print(f"WARNING: {summary['WARNING']}")
    print(f"INFO: {summary['INFO']}")
    print(f"source_id_closure: {summary['source_id_closure']}")
    print(f"evidence_id_closure: {summary['evidence_id_closure']}")
    print(f"no_investment_conclusion: {summary['no_investment_conclusion']}")
    print(f"score_placeholder: {summary['score_placeholder']}")
    print(f"formal_directory_pollution: {summary['formal_directory_pollution']}")
    print(f"validate_outputs_exit_code: {summary['validate_outputs_exit_code']}")
    print(f"recommend_next_stage: {summary['recommend_next_stage']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit gated formal staging outputs.")
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
