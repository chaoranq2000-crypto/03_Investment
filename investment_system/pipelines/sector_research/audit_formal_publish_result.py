"""Audit the result of a sector-card-only formal publish."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from investment_system.pipelines.sector_research.load_project import WORKSPACE_ROOT, load_project, resolve_output_path
from investment_system.pipelines.sector_research.prepare_formal_publish import (
    PUBLISH_LOG_PREFIX,
    SECTOR_CARD_ONLY,
)


FORBIDDEN_PATTERNS = [
    re.compile(r"建议买入|买入建议|买入评级"),
    re.compile(r"建议卖出|卖出建议|卖出评级"),
    re.compile(r"建议建仓|建仓建议"),
    re.compile(r"建议加仓|加仓建议"),
    re.compile(r"建议减仓|减仓建议"),
    re.compile(r"建议清仓|清仓建议"),
    re.compile(r"目标价|目标市值"),
    re.compile(r"action_rating:\s*[ABCDE](\s|$)"),
    re.compile(r"suggested_action:\s*(买入|卖出|建仓|加仓|减仓|清仓)"),
]


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


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


def _latest_publish_log(project_id: str, sector_id: str) -> Path:
    audit_dir = WORKSPACE_ROOT / "investment_system" / "research" / "projects" / project_id / "audits"
    matches = sorted(audit_dir.glob(f"{PUBLISH_LOG_PREFIX}_{sector_id}_*.json"))
    if not matches:
        return audit_dir / f"{PUBLISH_LOG_PREFIX}_{sector_id}.json"
    return matches[-1]


def _path_unchanged(record: dict[str, Any]) -> bool:
    before = record.get("before") or {}
    after = record.get("after") or {}
    return record.get("unchanged") is True and before == after


def _run_id_from_publish_log(path: Path, sector_id: str) -> str:
    prefix = f"{PUBLISH_LOG_PREFIX}_{sector_id}_"
    if path.stem.startswith(prefix):
        return path.stem[len(prefix) :]
    return datetime.now().strftime("%Y%m%d")


def audit_project(
    project_id: str,
    sector_id: str,
    *,
    publish_log_arg: str | None = None,
    write_report: bool = True,
) -> tuple[list[Finding], dict[str, Any]]:
    config = load_project(project_id, create_dirs=False, strict=False, silent=True)
    findings: list[Finding] = []
    publish_log_path = Path(publish_log_arg) if publish_log_arg else _latest_publish_log(project_id, sector_id)
    if publish_log_arg and not publish_log_path.is_absolute():
        publish_log_path = WORKSPACE_ROOT / publish_log_path

    if not publish_log_path.exists():
        findings.append(Finding("ERROR", "PUBLISH_LOG_MISSING", "publish log does not exist.", str(publish_log_path)))
        publish_log: dict[str, Any] = {}
    else:
        publish_log = json.loads(publish_log_path.read_text(encoding="utf-8"))
        findings.append(Finding("INFO", "PUBLISH_LOG_PRESENT", "publish log exists.", str(publish_log_path)))

    expected_target = Path(resolve_output_path(config, "sector_card", sector_id))
    source = Path(publish_log.get("source_gated_file", "")) if publish_log else Path()
    target = Path(publish_log.get("target_formal_file", "")) if publish_log else Path()
    source_hash = publish_log.get("source_hash") if publish_log else None
    target_hash = publish_log.get("target_hash") if publish_log else None
    release_manifest_path = Path(publish_log.get("release_manifest", "")) if publish_log else Path()

    if publish_log:
        if publish_log.get("project_id") != project_id:
            findings.append(Finding("ERROR", "PROJECT_ID_MISMATCH", f"project_id={publish_log.get('project_id')}"))
        if publish_log.get("sector_id") != sector_id:
            findings.append(Finding("ERROR", "SECTOR_ID_MISMATCH", f"sector_id={publish_log.get('sector_id')}"))
        if publish_log.get("publish_scope") != SECTOR_CARD_ONLY:
            findings.append(Finding("ERROR", "PUBLISH_SCOPE_INVALID", f"publish_scope={publish_log.get('publish_scope')}"))
        if publish_log.get("confirm_publish") is not True:
            findings.append(Finding("ERROR", "CONFIRM_PUBLISH_NOT_TRUE", "confirm_publish is not true."))
        if publish_log.get("overwrite") is not False:
            findings.append(Finding("ERROR", "OVERWRITE_NOT_FALSE", "overwrite is not false."))
        if publish_log.get("gates_passed") is not True:
            findings.append(Finding("ERROR", "GATES_NOT_PASSED", "gates_passed is not true."))
        if publish_log.get("investment_advice") is not False:
            findings.append(Finding("ERROR", "INVESTMENT_ADVICE_FLAG_INVALID", "investment_advice is not false."))
        if publish_log.get("score_status") != "score_placeholder_not_applicable":
            findings.append(Finding("ERROR", "SCORE_STATUS_INVALID", f"score_status={publish_log.get('score_status')}"))

        published_files = publish_log.get("published_files", {}) or {}
        if set(published_files) != {"sector_card"}:
            findings.append(Finding("ERROR", "PUBLISHED_FILES_SCOPE_INVALID", f"published_files={sorted(published_files)}"))
        else:
            findings.append(Finding("INFO", "SECTOR_CARD_ONLY_PUBLISHED", "published_files contains only sector_card."))
        if publish_log.get("published_file_count") != 1:
            findings.append(Finding("ERROR", "PUBLISHED_FILE_COUNT_INVALID", f"published_file_count={publish_log.get('published_file_count')}"))
        if publish_log.get("published_file_types") != ["sector_card"]:
            findings.append(Finding("ERROR", "PUBLISHED_FILE_TYPES_INVALID", f"published_file_types={publish_log.get('published_file_types')}"))

        if not source.exists():
            findings.append(Finding("ERROR", "SOURCE_GATED_FILE_MISSING", "source gated file missing.", str(source)))
        if not target.exists():
            findings.append(Finding("ERROR", "TARGET_SECTOR_CARD_MISSING", "formal sector card missing.", str(target)))
        if target and target.resolve() != expected_target.resolve():
            findings.append(Finding("ERROR", "TARGET_PATH_MISMATCH", "formal sector card target differs from project-aware path.", str(target)))
        if not release_manifest_path.exists():
            findings.append(Finding("ERROR", "RELEASE_MANIFEST_MISSING", "release manifest from publish log does not exist.", str(release_manifest_path)))
        else:
            release_manifest = json.loads(release_manifest_path.read_text(encoding="utf-8"))
            manifest_target = release_manifest.get("formal_target_paths_read_only", {}).get("sector_card")
            if manifest_target != str(target):
                findings.append(Finding("ERROR", "TARGET_PATH_NOT_MANIFEST_TARGET", "formal sector card target differs from release manifest.", str(target)))
            else:
                findings.append(Finding("INFO", "TARGET_PATH_MATCHES_MANIFEST", "formal sector card path equals release manifest target."))
        if source.exists() and _sha256(source) != source_hash:
            findings.append(Finding("ERROR", "SOURCE_HASH_CHANGED", "source hash no longer matches publish log.", str(source)))
        if target.exists() and _sha256(target) != target_hash:
            findings.append(Finding("ERROR", "TARGET_HASH_CHANGED", "target hash no longer matches publish log.", str(target)))
        if source_hash != target_hash:
            findings.append(Finding("ERROR", "SOURCE_TARGET_HASH_MISMATCH", "source hash and target hash differ."))
        elif source_hash and target_hash:
            findings.append(Finding("INFO", "SOURCE_TARGET_HASH_OK", "source hash equals target hash."))

        skipped = publish_log.get("skipped_outputs", {}) or {}
        required_skipped = {
            "company_table",
            "sector_comparison_table",
            "source_index",
            "missing_data_log",
            "conflict_data_log",
            "score_table",
        }
        missing_skipped = sorted(required_skipped - set(skipped))
        if missing_skipped:
            findings.append(Finding("ERROR", "SKIPPED_OUTPUT_RECORDS_MISSING", ", ".join(missing_skipped)))
        changed = [name for name, record in skipped.items() if not _path_unchanged(record)]
        if changed:
            findings.append(Finding("ERROR", "NON_SECTOR_OUTPUT_CHANGED", ", ".join(sorted(changed))))
        else:
            findings.append(Finding("INFO", "NON_SECTOR_OUTPUTS_UNCHANGED", "shared tables/logs/score targets unchanged."))

    if target.exists():
        content = target.read_text(encoding="utf-8-sig", errors="ignore")
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(content):
                findings.append(Finding("ERROR", "FORMAL_INVESTMENT_LANGUAGE", f"sector_card matched {pattern.pattern}", str(target)))
        for token in ["action_rating: NOT_RATED", "suggested_action: FORMAL_GATED_REVIEW_ONLY", "investment_conclusion: NOT_INVESTMENT_ADVICE"]:
            if token not in content:
                findings.append(Finding("ERROR", "NO_ADVICE_MARKER_MISSING", f"sector_card missing {token}", str(target)))
        if not any(f.code == "FORMAL_INVESTMENT_LANGUAGE" for f in findings):
            findings.append(Finding("INFO", "NO_INVESTMENT_CONCLUSION_OK", "No forbidden investment wording found in published sector card."))
        if "score_placeholder_not_applicable" in content or "score_placeholder" in content or "not_applicable" in content:
            findings.append(Finding("INFO", "SCORE_PLACEHOLDER_OK", "Published card retains score placeholder/not_applicable status."))

    validate_exit, _validate_output = _run_module("investment_system.pipelines.validate_outputs", "--project", project_id)
    if validate_exit == 0:
        findings.append(Finding("INFO", "VALIDATE_OUTPUTS_OK", "validate_outputs exit_code=0."))
    else:
        findings.append(Finding("ERROR", "VALIDATE_OUTPUTS_FAILED", f"validate_outputs exit_code={validate_exit}"))

    counts = _counts(findings)
    summary = {
        **counts,
        "audit_time": _now_iso(),
        "project_id": project_id,
        "sector_id": sector_id,
        "publish_scope": publish_log.get("publish_scope") if publish_log else None,
        "publish_log_path": str(publish_log_path),
        "release_manifest_path": str(release_manifest_path) if publish_log else "",
        "source_gated_file": str(source) if publish_log else "",
        "target_formal_file": str(target) if publish_log else "",
        "source_hash": source_hash,
        "target_hash": target_hash,
        "hash_match": bool(source_hash and target_hash and source_hash == target_hash),
        "overwrite": publish_log.get("overwrite") if publish_log else None,
        "sector_card_exists": target.exists() if publish_log else False,
        "sector_card_only": publish_log.get("publish_scope") == SECTOR_CARD_ONLY and set((publish_log.get("published_files", {}) or {})) == {"sector_card"} if publish_log else False,
        "published_file_count": publish_log.get("published_file_count") if publish_log else None,
        "published_file_types": publish_log.get("published_file_types") if publish_log else None,
        "non_sector_outputs_unchanged": publish_log.get("non_sector_outputs_unchanged") if publish_log else None,
        "no_investment_conclusion": not any(f.code == "FORMAL_INVESTMENT_LANGUAGE" for f in findings),
        "score_placeholder": publish_log.get("score_status") == "score_placeholder_not_applicable" if publish_log else None,
        "validate_outputs_exit_code": validate_exit,
        "recommend_next_stage": counts["ERROR"] == 0,
    }
    if write_report:
        _write_report(findings, summary)
    return findings, summary


def _write_report(findings: list[Finding], summary: dict[str, Any]) -> None:
    audit_dir = WORKSPACE_ROOT / "investment_system" / "research" / "projects" / summary["project_id"] / "audits"
    audit_dir.mkdir(parents=True, exist_ok=True)
    run_id = _run_id_from_publish_log(Path(summary["publish_log_path"]), summary["sector_id"])
    path = audit_dir / f"formal_publish_result_audit_{summary['sector_id']}_{run_id}.md"
    lines = [
        "# Formal Publish Result Audit",
        "",
        f"- audit_time: {summary['audit_time']}",
        f"- project_id: `{summary['project_id']}`",
        f"- sector_id: `{summary['sector_id']}`",
        f"- publish_scope: `{summary['publish_scope']}`",
        f"- publish_log: `{summary['publish_log_path']}`",
        f"- release_manifest: `{summary['release_manifest_path']}`",
        f"- 发布源文件: `{summary['source_gated_file']}`",
        f"- 发布目标文件: `{summary['target_formal_file']}`",
        f"- source_hash: `{summary['source_hash']}`",
        f"- target_hash: `{summary['target_hash']}`",
        f"- source_target_hash_match: {summary['hash_match']}",
        f"- overwrite: {summary['overwrite']}",
        f"- sector_card_only: {summary['sector_card_only']}",
        f"- published_file_count: {summary['published_file_count']}",
        f"- published_file_types: {summary['published_file_types']}",
        f"- non_sector_outputs_unchanged: {summary['non_sector_outputs_unchanged']}",
        f"- no_investment_conclusion: {summary['no_investment_conclusion']}",
        f"- score_placeholder_not_applicable: {summary['score_placeholder']}",
        f"- validate_outputs_exit_code: {summary['validate_outputs_exit_code']}",
        "",
        "## ERROR/WARNING/INFO 汇总",
        f"- ERROR: {summary['ERROR']}",
        f"- WARNING: {summary['WARNING']}",
        f"- INFO: {summary['INFO']}",
        f"- recommend_next_stage: {summary['recommend_next_stage']}",
        "",
        "## Findings",
    ]
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
    print("Formal Publish Result Audit")
    print("=" * 60)
    print(f"project_id: {summary['project_id']}")
    print(f"sector_id: {summary['sector_id']}")
    print(f"publish_scope: {summary['publish_scope']}")
    print(f"publish_log: {summary['publish_log_path']}")
    print(f"target_formal_file: {summary['target_formal_file']}")
    print(f"ERROR: {summary['ERROR']}")
    print(f"WARNING: {summary['WARNING']}")
    print(f"INFO: {summary['INFO']}")
    print(f"sector_card_only: {summary['sector_card_only']}")
    print(f"non_sector_outputs_unchanged: {summary['non_sector_outputs_unchanged']}")
    print(f"hash_match: {summary['hash_match']}")
    print(f"no_investment_conclusion: {summary['no_investment_conclusion']}")
    print(f"score_placeholder: {summary['score_placeholder']}")
    print(f"validate_outputs_exit_code: {summary['validate_outputs_exit_code']}")
    print(f"recommend_next_stage: {summary['recommend_next_stage']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit a sector-card-only formal publish result.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--sector-id", required=True)
    parser.add_argument("--publish-log", default=None)
    args = parser.parse_args(argv)

    findings, summary = audit_project(
        args.project,
        args.sector_id,
        publish_log_arg=args.publish_log,
        write_report=True,
    )
    _print_summary(summary)
    if summary["ERROR"]:
        print("Errors:")
        for finding in findings:
            if finding.severity == "ERROR":
                print(f"  [{finding.code}] {finding.message} {finding.file}")
    return 1 if summary["ERROR"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
