"""Audit formal publish readiness manifest before any final output write."""

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

from investment_system.pipelines.sector_research.load_project import WORKSPACE_ROOT, load_project
from investment_system.pipelines.sector_research.prepare_formal_publish import (
    MANIFEST_PREFIX,
    PUBLISH_STATUS,
    SECTOR_CARD_ONLY,
    default_manifest_path,
    resolve_final_publish_paths,
)
from investment_system.pipelines.sector_research.promote_formal_candidate_outputs import FORBIDDEN_PATTERNS, get_gated_formal_output_dir


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


def _latest_manifest(project_id: str, sector_id: str) -> Path:
    audit_dir = WORKSPACE_ROOT / "investment_system" / "research" / "projects" / project_id / "audits"
    matches = sorted(audit_dir.glob(f"{MANIFEST_PREFIX}_{sector_id}_*.json"))
    if matches:
        return matches[-1]
    return default_manifest_path(project_id, sector_id)


def _manifest_path(project_id: str, sector_id: str, raw: str | None) -> Path:
    if raw:
        path = Path(raw)
        return path if path.is_absolute() else WORKSPACE_ROOT / path
    return _latest_manifest(project_id, sector_id)


def audit_project(
    project_id: str,
    sector_id: str,
    *,
    manifest_path_arg: str | None = None,
    write_report: bool = True,
) -> tuple[list[Finding], dict[str, Any]]:
    config = load_project(project_id, create_dirs=False, strict=False, silent=True)
    findings: list[Finding] = []
    manifest_path = _manifest_path(project_id, sector_id, manifest_path_arg)
    gated_root = get_gated_formal_output_dir(config).resolve()
    all_final_paths = resolve_final_publish_paths(config, sector_id)
    formal_root = config.output_root.resolve()

    if not manifest_path.exists():
        findings.append(Finding("ERROR", "RELEASE_MANIFEST_MISSING", "release manifest does not exist.", str(manifest_path)))
        manifest: dict[str, Any] = {}
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        findings.append(Finding("INFO", "RELEASE_MANIFEST_PRESENT", "release manifest exists.", str(manifest_path)))

    if manifest:
        if manifest.get("project_id") != project_id:
            findings.append(Finding("ERROR", "PROJECT_ID_MISMATCH", f"manifest project_id={manifest.get('project_id')}"))
        if manifest.get("sector_id") != sector_id:
            findings.append(Finding("ERROR", "SECTOR_ID_MISMATCH", f"manifest sector_id={manifest.get('sector_id')}"))
        if manifest.get("publish_executed") is not False:
            findings.append(Finding("ERROR", "PUBLISH_ALREADY_EXECUTED", "manifest publish_executed is not false."))
        if manifest.get("dry_run") is not True:
            findings.append(Finding("ERROR", "PUBLISH_NOT_DRY_RUN", "manifest dry_run is not true."))
        if manifest.get("publish_status") != PUBLISH_STATUS:
            findings.append(Finding("ERROR", "PUBLISH_STATUS_INVALID", f"publish_status={manifest.get('publish_status')}"))
        if manifest.get("manual_confirmation_required") is not True:
            findings.append(Finding("ERROR", "MANUAL_CONFIRMATION_NOT_REQUIRED", "manual_confirmation_required is not true."))
        publish_scope = manifest.get("publish_scope")
        if publish_scope == SECTOR_CARD_ONLY:
            final_paths = {"sector_card": all_final_paths["sector_card"]}
        else:
            final_paths = all_final_paths

        gate_status = manifest.get("gate_status", {}) or {}
        expected_true = [
            "source_id_closure",
            "evidence_id_closure",
            "no_investment_conclusion",
            "score_placeholder",
            "formal_directory_pollution",
            "all_sources_from_gated_staging",
            "gates_passed",
        ]
        for key in expected_true:
            if gate_status.get(key) is not True:
                findings.append(Finding("ERROR", "GATE_STATUS_NOT_PASSING", f"{key}={gate_status.get(key)}"))
        if gate_status.get("gated_formal_audit_error_count") != 0:
            findings.append(Finding("ERROR", "GATED_AUDIT_ERROR_COUNT_NONZERO", f"ERROR={gate_status.get('gated_formal_audit_error_count')}"))
        if gate_status.get("validate_outputs_exit_code") != 0:
            findings.append(Finding("ERROR", "VALIDATE_OUTPUTS_NOT_ZERO_IN_MANIFEST", f"exit={gate_status.get('validate_outputs_exit_code')}"))

        manifest_targets = manifest.get("formal_target_paths_read_only", {}) or {}
        if publish_scope == SECTOR_CARD_ONLY and set(manifest_targets) != {"sector_card"}:
            findings.append(Finding("ERROR", "SECTOR_CARD_ONLY_TARGET_SCOPE_INVALID", f"targets={sorted(manifest_targets)}"))
        for output_type, expected_path in final_paths.items():
            if manifest_targets.get(output_type) != expected_path:
                findings.append(Finding("ERROR", "TARGET_PATH_NOT_PROJECT_AWARE", f"{output_type} target mismatch."))
        findings.append(Finding("INFO", "FINAL_TARGET_PATHS_RESOLVED", f"target_count={len(manifest_targets)}"))

        file_rows = manifest.get("file_map", []) or []
        if not file_rows:
            findings.append(Finding("ERROR", "MANIFEST_FILE_MAP_EMPTY", "file_map is empty."))
        if publish_scope == SECTOR_CARD_ONLY:
            row_types = {row.get("output_type") for row in file_rows}
            if row_types != {"sector_card"}:
                findings.append(Finding("ERROR", "SECTOR_CARD_ONLY_FILE_MAP_INVALID", f"file_map output_types={sorted(row_types)}"))
        for row in file_rows:
            source = Path(row.get("source_path", ""))
            target = Path(row.get("target_path", ""))
            if not source.exists():
                findings.append(Finding("ERROR", "SOURCE_FILE_MISSING", "source file missing.", str(source)))
                continue
            if not str(source.resolve()).startswith(str(gated_root)):
                findings.append(Finding("ERROR", "SOURCE_NOT_FROM_GATED_STAGING", "source is not under gated staging.", str(source)))
            if str(source.resolve()).startswith(str(formal_root)):
                findings.append(Finding("ERROR", "SOURCE_IN_FINAL_OUTPUT_ROOT", "source is inside final formal output root.", str(source)))
            if _sha256(source) != row.get("sha256"):
                findings.append(Finding("ERROR", "SOURCE_HASH_MISMATCH", "source sha256 mismatch.", str(source)))
            if source.stat().st_size != row.get("size_bytes"):
                findings.append(Finding("ERROR", "SOURCE_SIZE_MISMATCH", "source size mismatch.", str(source)))
            if str(target).startswith(str(gated_root)):
                findings.append(Finding("ERROR", "TARGET_POINTS_TO_GATED_STAGING", "target points to gated staging.", str(target)))
            if not str(target).startswith(str(formal_root)):
                findings.append(Finding("ERROR", "TARGET_NOT_UNDER_PROJECT_OUTPUT_ROOT", "target is not under project output root.", str(target)))
            if row.get("output_type") == "sector_card" and target.exists():
                findings.append(Finding("ERROR", "TARGET_SECTOR_CARD_ALREADY_EXISTS", "sector_card target already exists; no-overwrite publish would be blocked.", str(target)))
            if row.get("overwrite_risk"):
                findings.append(Finding("ERROR", "OVERWRITE_RISK", f"overwrite risk for {row.get('output_type')}", str(target)))
            if row.get("non_sector_overwrite_risk"):
                findings.append(Finding("ERROR", "NON_SECTOR_OVERWRITE_RISK", f"non-sector overwrite risk for {row.get('output_type')}", str(target)))
        if file_rows and not any(f.code in {"SOURCE_HASH_MISMATCH", "SOURCE_SIZE_MISMATCH"} for f in findings):
            findings.append(Finding("INFO", "SOURCE_HASH_SIZE_OK", f"verified {len(file_rows)} source files."))

        excluded = manifest.get("excluded_outputs_read_only", {}) or {}
        if publish_scope == SECTOR_CARD_ONLY:
            illegal_actions = [
                name
                for name, row in excluded.items()
                if row.get("publish_action") is not False
            ]
            if illegal_actions:
                findings.append(Finding("ERROR", "EXCLUDED_OUTPUT_HAS_PUBLISH_ACTION", f"outputs={sorted(illegal_actions)}"))
            unexpected_publish_rows = [
                row.get("output_type")
                for row in file_rows
                if row.get("output_type") in {
                    "company_table",
                    "sector_comparison_table",
                    "source_index",
                    "missing_data_log",
                    "conflict_data_log",
                    "score_table",
                    "release_manifest",
                }
            ]
            if unexpected_publish_rows:
                findings.append(Finding("ERROR", "NON_SECTOR_OUTPUT_PUBLISH_ACTION", f"outputs={sorted(unexpected_publish_rows)}"))
            if not illegal_actions and not unexpected_publish_rows:
                findings.append(Finding("INFO", "SECTOR_CARD_ONLY_SCOPE_OK", "Only sector_card is mapped for potential publish; other outputs are excluded/no-action."))

        for path_text in [str(manifest_path), manifest.get("gated_formal_root", ""), manifest.get("gated_metadata_path", "")]:
            if path_text and str(Path(path_text).resolve()).startswith(str(formal_root)):
                findings.append(Finding("ERROR", "AUDIT_ARTIFACT_IN_FINAL_OUTPUT_ROOT", f"audit artifact under final output root: {path_text}"))

        for output_type, path_text in (manifest.get("gated_formal_files", {}) or {}).items():
            path = Path(path_text)
            if path.exists():
                content = path.read_text(encoding="utf-8-sig", errors="ignore")
                for pattern in FORBIDDEN_PATTERNS:
                    if pattern.search(content):
                        findings.append(Finding("ERROR", "FORMAL_INVESTMENT_LANGUAGE", f"{output_type} matched {pattern.pattern}", str(path)))

    validate_exit, _validate_output = _run_module("investment_system.pipelines.validate_outputs", "--project", project_id)
    if validate_exit == 0:
        findings.append(Finding("INFO", "VALIDATE_OUTPUTS_OK", "validate_outputs exit_code=0."))
    else:
        findings.append(Finding("ERROR", "VALIDATE_OUTPUTS_FAILED", f"validate_outputs exit_code={validate_exit}"))

    if not any(f.code == "FORMAL_INVESTMENT_LANGUAGE" for f in findings):
        findings.append(Finding("INFO", "NO_INVESTMENT_CONCLUSION_OK", "No forbidden investment wording found in gated files."))
    if manifest and manifest.get("gate_status", {}).get("score_placeholder") is True:
        findings.append(Finding("INFO", "SCORE_PLACEHOLDER_OK", "score remains placeholder/not_applicable."))
    if manifest and manifest.get("gate_status", {}).get("formal_directory_pollution") is True:
        findings.append(Finding("INFO", "FORMAL_DIRECTORY_POLLUTION_OK", "No final output write detected by gated audit."))

    counts = _counts(findings)
    summary = {
        **counts,
        "audit_time": _now_iso(),
        "project_id": project_id,
        "sector_id": sector_id,
        "manifest_path": str(manifest_path),
        "gated_formal_root": manifest.get("gated_formal_root", "") if manifest else "",
        "final_target_paths": manifest.get("formal_target_paths_read_only", {}) if manifest else {},
        "excluded_outputs": manifest.get("excluded_outputs_read_only", {}) if manifest else {},
        "publish_scope": manifest.get("publish_scope") if manifest else None,
        "dry_run": manifest.get("dry_run") if manifest else None,
        "confirm_publish_requested": manifest.get("confirm_publish_requested") if manifest else None,
        "publish_executed": manifest.get("publish_executed") if manifest else None,
        "manual_confirmation_required": manifest.get("manual_confirmation_required") if manifest else None,
        "source_id_closure": (manifest.get("gate_status", {}) or {}).get("source_id_closure") if manifest else None,
        "evidence_id_closure": (manifest.get("gate_status", {}) or {}).get("evidence_id_closure") if manifest else None,
        "no_investment_conclusion": not any(f.code == "FORMAL_INVESTMENT_LANGUAGE" for f in findings),
        "score_placeholder": (manifest.get("gate_status", {}) or {}).get("score_placeholder") if manifest else None,
        "target_overwrite_risk": (manifest.get("gate_status", {}) or {}).get("target_overwrite_risk") if manifest else None,
        "formal_directory_pollution": (manifest.get("gate_status", {}) or {}).get("formal_directory_pollution") if manifest else None,
        "validate_outputs_exit_code": validate_exit,
        "recommend_next_stage": counts["ERROR"] == 0,
    }
    if write_report:
        _write_report(findings, summary)
    return findings, summary


def _write_report(findings: list[Finding], summary: dict[str, Any]) -> None:
    audit_dir = WORKSPACE_ROOT / "investment_system" / "research" / "projects" / summary["project_id"] / "audits"
    audit_dir.mkdir(parents=True, exist_ok=True)
    path = audit_dir / "formal_publish_readiness_audit.md"
    lines = [
        "# Formal Publish Readiness Audit",
        "",
        f"- audit_time: {summary['audit_time']}",
        f"- project_id: `{summary['project_id']}`",
        f"- sector_id: `{summary['sector_id']}`",
        f"- gated formal source: `{summary['gated_formal_root']}`",
        f"- release manifest: `{summary['manifest_path']}`",
        f"- publish_scope: `{summary['publish_scope']}`",
        f"- dry_run: {summary['dry_run']}",
        f"- manual_confirmation_required: {summary['manual_confirmation_required']}",
        f"- confirm_publish_requested: {summary['confirm_publish_requested']}",
        f"- publish_executed: {summary['publish_executed']}",
        "",
        "## 最终正式发布目标路径清单",
    ]
    for name, target in summary["final_target_paths"].items():
        lines.append(f"- {name}: `{target}`")
    if summary.get("excluded_outputs"):
        lines.extend([
            "",
            "## 明确排除的正式输出动作",
        ])
        for name, row in summary["excluded_outputs"].items():
            lines.append(f"- {name}: publish_action={row.get('publish_action')}; target=`{row.get('target_path')}`")
    lines.extend([
        "",
        "## 门禁结果",
        f"- source_id_closure: {summary['source_id_closure']}",
        f"- evidence_id_closure: {summary['evidence_id_closure']}",
        f"- no_investment_conclusion: {summary['no_investment_conclusion']}",
        f"- score_placeholder_not_applicable: {summary['score_placeholder']}",
        f"- target_overwrite_risk: {summary['target_overwrite_risk']}",
        f"- formal_directory_pollution: {summary['formal_directory_pollution']}",
        f"- validate_outputs_exit_code: {summary['validate_outputs_exit_code']}",
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
    print("Formal Publish Readiness Audit")
    print("=" * 60)
    print(f"project_id: {summary['project_id']}")
    print(f"sector_id: {summary['sector_id']}")
    print(f"manifest_path: {summary['manifest_path']}")
    print(f"publish_scope: {summary['publish_scope']}")
    print(f"ERROR: {summary['ERROR']}")
    print(f"WARNING: {summary['WARNING']}")
    print(f"INFO: {summary['INFO']}")
    print(f"dry_run: {summary['dry_run']}")
    print(f"publish_executed: {summary['publish_executed']}")
    print(f"manual_confirmation_required: {summary['manual_confirmation_required']}")
    print(f"source_id_closure: {summary['source_id_closure']}")
    print(f"evidence_id_closure: {summary['evidence_id_closure']}")
    print(f"no_investment_conclusion: {summary['no_investment_conclusion']}")
    print(f"score_placeholder: {summary['score_placeholder']}")
    print(f"target_overwrite_risk: {summary['target_overwrite_risk']}")
    print(f"formal_directory_pollution: {summary['formal_directory_pollution']}")
    print(f"validate_outputs_exit_code: {summary['validate_outputs_exit_code']}")
    print(f"recommend_next_stage: {summary['recommend_next_stage']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit formal publish readiness release manifest.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--sector-id", required=True)
    parser.add_argument("--release-manifest", default=None)
    args = parser.parse_args(argv)

    findings, summary = audit_project(
        args.project,
        args.sector_id,
        manifest_path_arg=args.release_manifest,
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
