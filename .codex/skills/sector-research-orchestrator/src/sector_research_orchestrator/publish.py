"""Prepare or execute a tightly scoped formal publication.

The default behavior is rehearsal only: resolve final project-aware output paths,
verify gated formal staging, and write a release manifest under audits.

Confirmed publication is intentionally narrow. It currently supports only
``--publish-scope sector_card_only`` and refuses overwrite or any shared-table
write.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from investment_system.core.skill_module_loader import skill_subprocess_env
from quality_auditor.gated_outputs import audit_project as audit_gated_project
from research_writer.candidate_outputs import (
    get_candidate_paths,
    get_formal_candidate_output_dir,
)
from investment_system.core.project_loader import (
    WORKSPACE_ROOT,
    ProjectConfig,
    load_project,
    resolve_output_path,
)
from sector_research_orchestrator.promote import (
    GATED_STATUS,
    NO_ADVICE,
    NOT_RATED,
    REQUIRED_OUTPUTS,
    get_gated_formal_output_dir,
)


MANIFEST_PREFIX = "formal_publish_manifest"
PUBLISH_LOG_PREFIX = "formal_publish_log"
PUBLISH_STATUS = "awaiting_manual_confirmation"
PUBLISHED_STATUS = "published_sector_card_only"
SECTOR_CARD_ONLY = "sector_card_only"
REHEARSAL_SCOPE = "all_outputs_rehearsal"
SOURCE_STAGE_CANDIDATE = "formal_candidate"
SOURCE_STAGE_GATED = "gated_formal"
SHARED_OUTPUTS = {
    "company_table",
    "sector_comparison_table",
    "source_index",
    "missing_data_log",
    "conflict_data_log",
    "score_table",
    "release_manifest",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _date_id() -> str:
    return datetime.now().strftime("%Y%m%d")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolve_root(raw: str | None, default: Path) -> Path:
    if not raw:
        return default
    path = Path(raw)
    return path if path.is_absolute() else WORKSPACE_ROOT / path


def _audit_dir(project_id: str) -> Path:
    return WORKSPACE_ROOT / "investment_system" / "research" / "projects" / project_id / "audits"


def default_manifest_path(project_id: str, sector_id: str) -> Path:
    return _audit_dir(project_id) / f"{MANIFEST_PREFIX}_{sector_id}_{_date_id()}.json"


def default_publish_log_path(project_id: str, sector_id: str, run_id: str | None = None) -> Path:
    return _audit_dir(project_id) / f"{PUBLISH_LOG_PREFIX}_{sector_id}_{run_id or _date_id()}.json"


def _latest_gated_metadata(gated_root: Path, sector_id: str) -> Path:
    matches = sorted(
        gated_root.glob(f"gated_formal_{sector_id}_*_metadata.json"),
        key=lambda path: (_metadata_run_id("gated_formal", sector_id, path), path.stat().st_mtime),
    )
    if not matches:
        raise FileNotFoundError(f"No gated formal metadata found for {sector_id} in {gated_root}")
    return matches[-1]


def _latest_candidate_metadata(candidate_root: Path, sector_id: str) -> Path:
    matches = sorted(
        candidate_root.glob(f"formal_candidate_{sector_id}_*_metadata.json"),
        key=lambda path: (_metadata_run_id("formal_candidate", sector_id, path), path.stat().st_mtime),
    )
    if not matches:
        raise FileNotFoundError(f"No formal candidate metadata found for {sector_id} in {candidate_root}")
    return matches[-1]


def _metadata_run_id(prefix: str, sector_id: str, path: Path) -> str:
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
        run_id = str(metadata.get("run_id") or "").strip()
        if run_id:
            return run_id
    except (OSError, json.JSONDecodeError):
        pass
    match = re.match(rf"{re.escape(prefix)}_{re.escape(sector_id)}_(.+)_metadata\.json$", path.name)
    return match.group(1) if match else ""


def resolve_final_publish_paths(config: ProjectConfig, sector_id: str, run_id: str | None = None) -> dict[str, str]:
    result: dict[str, str] = {}
    for output_type in REQUIRED_OUTPUTS:
        result[output_type] = resolve_output_path(
            config,
            output_type,
            sector_id if output_type == "sector_card" else None,
        )
    rid = run_id or _date_id()
    result["release_manifest"] = str(config.logs_dir / f"{MANIFEST_PREFIX}_{sector_id}_{rid}.json")
    return result


def _publish_output_types(publish_scope: str) -> list[str]:
    if publish_scope == SECTOR_CARD_ONLY:
        return ["sector_card"]
    return list(REQUIRED_OUTPUTS)


def _check_gated_metadata(metadata: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if metadata.get("action_rating") != NOT_RATED:
        errors.append(f"action_rating is not {NOT_RATED}")
    if metadata.get("suggested_action") != GATED_STATUS:
        errors.append(f"suggested_action is not {GATED_STATUS}")
    if metadata.get("investment_conclusion") != NO_ADVICE:
        errors.append(f"investment_conclusion is not {NO_ADVICE}")
    if metadata.get("score_status") != "score_placeholder_not_applicable":
        errors.append("score_status is not score_placeholder_not_applicable")
    candidate_audit = metadata.get("candidate_audit") or {}
    if candidate_audit.get("ERROR") != 0:
        errors.append(f"candidate_audit ERROR is {candidate_audit.get('ERROR')}")
    if not candidate_audit.get("source_id_closure"):
        errors.append("candidate_audit source_id_closure is false")
    if not candidate_audit.get("evidence_id_closure"):
        errors.append("candidate_audit evidence_id_closure is false")
    return errors


def _check_candidate_metadata(metadata: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if metadata.get("candidate_status") != "publish_gate_ready":
        errors.append(f"candidate_status is not publish_gate_ready: {metadata.get('candidate_status')}")
    if metadata.get("gated_formal_generated") is not False:
        errors.append("gated_formal_generated is not false")
    if metadata.get("formal_output_root_written") is not False:
        errors.append("formal_output_root_written is not false")
    gate = metadata.get("candidate_gate") or {}
    if gate.get("status") != "PASS":
        errors.append(f"candidate_gate status is not PASS: {gate.get('status')}")
    if gate.get("error_count") != 0:
        errors.append(f"candidate_gate error_count is {gate.get('error_count')}")
    if gate.get("validate_outputs_exit_code") not in {0, None}:
        errors.append(f"candidate_gate validate_outputs_exit_code is {gate.get('validate_outputs_exit_code')}")
    if gate.get("readiness_blocker") not in {0, None}:
        errors.append(f"candidate_gate readiness_blocker is {gate.get('readiness_blocker')}")
    if gate.get("readiness_high") not in {0, None}:
        errors.append(f"candidate_gate readiness_high is {gate.get('readiness_high')}")
    if gate.get("recommend_publish_gate") is not True:
        errors.append("candidate_gate recommend_publish_gate is not true")
    return errors


def _source_record(
    *,
    output_type: str,
    source_path: Path,
    target_path: Path,
    gated_root: Path,
    candidate_root: Path,
) -> dict[str, Any]:
    target_exists = target_path.exists()
    shared_target = output_type in SHARED_OUTPUTS
    return {
        "output_type": output_type,
        "source_path": str(source_path),
        "source_from_gated_staging": str(source_path.resolve()).startswith(str(gated_root.resolve())),
        "source_from_candidate_staging": str(source_path.resolve()).startswith(str(candidate_root.resolve())),
        "target_path": str(target_path),
        "target_exists": target_exists,
        "write_mode_if_confirmed_future": "append_or_merge" if shared_target else "create_or_replace_same_sector_only",
        "overwrite_risk": bool(target_exists and not shared_target),
        "non_sector_overwrite_risk": False,
        "sha256": _sha256(source_path),
        "size_bytes": source_path.stat().st_size,
    }


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="ignore")


def _snapshot_path(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "sha256": None, "size_bytes": None}
    return {"exists": True, "sha256": _sha256(path), "size_bytes": path.stat().st_size}


def _run_readiness_audit(project_id: str, sector_id: str, manifest_arg: str | None = None) -> tuple[int, str]:
    cmd = [
        sys.executable,
        "-m",
        "quality_auditor.publish_readiness",
        "--project",
        project_id,
        "--sector-id",
        sector_id,
    ]
    if manifest_arg:
        cmd.extend(["--release-manifest", manifest_arg])
    proc = subprocess.run(
        cmd,
        cwd=str(WORKSPACE_ROOT),
        env=skill_subprocess_env(),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _assert_confirm_publish_allowed(
    *,
    config: ProjectConfig,
    project_id: str,
    sector_id: str,
    manifest: dict[str, Any],
    publish_scope: str,
    no_overwrite: bool,
) -> dict[str, Any]:
    if publish_scope != SECTOR_CARD_ONLY:
        raise RuntimeError(f"--confirm-publish currently requires --publish-scope {SECTOR_CARD_ONLY}")
    if not no_overwrite:
        raise RuntimeError("--confirm-publish currently requires --no-overwrite")

    gate_status = manifest.get("gate_status", {}) or {}
    required_true = [
        "source_id_closure",
        "evidence_id_closure",
        "no_investment_conclusion",
        "score_placeholder",
        "formal_directory_pollution",
        "gates_passed",
    ]
    for key in required_true:
        if gate_status.get(key) is not True:
            raise RuntimeError(f"publish gate failed: {key}={gate_status.get(key)}")
    if gate_status.get("gated_formal_audit_error_count") != 0:
        raise RuntimeError(f"gated formal audit ERROR={gate_status.get('gated_formal_audit_error_count')}")
    source_stage = manifest.get("source_stage", SOURCE_STAGE_GATED)
    if source_stage == SOURCE_STAGE_CANDIDATE:
        if gate_status.get("all_sources_from_candidate_staging") is not True:
            raise RuntimeError("publish gate failed: all_sources_from_candidate_staging is not true")
        if gate_status.get("candidate_gate_error_count") != 0:
            raise RuntimeError(f"candidate gate ERROR={gate_status.get('candidate_gate_error_count')}")
    elif gate_status.get("all_sources_from_gated_staging") is not True:
        raise RuntimeError("publish gate failed: all_sources_from_gated_staging is not true")

    final_paths = manifest.get("formal_target_paths_read_only", {}) or {}
    expected_target = Path(resolve_final_publish_paths(config, sector_id, manifest.get("run_id")).get("sector_card", ""))
    target = Path(final_paths.get("sector_card", ""))
    if target.resolve() != expected_target.resolve():
        raise RuntimeError(f"sector_card target is not project-aware path: {target}")
    if str(target.resolve()).startswith(str(config.total_tables_dir.resolve())):
        raise RuntimeError("sector_card target resolves inside total tables directory")
    if str(target.resolve()).startswith(str(config.logs_dir.resolve())):
        raise RuntimeError("sector_card target resolves inside formal logs directory")
    if target.exists():
        raise RuntimeError(f"target sector card already exists and --no-overwrite is active: {target}")

    source_rows = {row.get("output_type"): row for row in manifest.get("file_map", []) or []}
    if set(source_rows) != {"sector_card"}:
        raise RuntimeError(f"sector_card_only publish manifest must contain only sector_card file_map rows: {sorted(source_rows)}")
    sector_row = source_rows.get("sector_card")
    if not sector_row:
        raise RuntimeError("release manifest lacks sector_card source row")
    source = Path(sector_row.get("source_path", ""))
    if not source.exists():
        raise RuntimeError(f"sector_card publish source missing: {source}")
    if _sha256(source) != sector_row.get("sha256"):
        raise RuntimeError("sector_card publish source hash changed after manifest creation")
    if sector_row.get("target_path") != str(target):
        raise RuntimeError("sector_card target path differs between file_map and final target paths")
    excluded = manifest.get("excluded_outputs_read_only", {}) or {}
    for output_type, row in excluded.items():
        if row.get("publish_action") is not False:
            raise RuntimeError(f"excluded output has publish_action enabled: {output_type}")
        if Path(row.get("target_path", "")).resolve() == target.resolve():
            raise RuntimeError(f"excluded output shares target path with sector_card: {output_type}")

    forbidden_terms = [
        "建议买入",
        "买入建议",
        "买入评级",
        "建议卖出",
        "卖出建议",
        "卖出评级",
        "建议建仓",
        "建仓建议",
        "建议加仓",
        "加仓建议",
        "建议减仓",
        "减仓建议",
        "建议清仓",
        "清仓建议",
        "目标价",
        "目标市值",
    ]
    text = _read_text(source)
    hits = [term for term in forbidden_terms if term in text]
    if hits:
        raise RuntimeError("sector_card contains forbidden investment language: " + ", ".join(hits))
    marker_groups = [
        ("NOT_RATED", ["action_rating: NOT_RATED", "rating_status: NOT_RATED", "score_status: `NOT_RATED`"]),
        ("NOT_INVESTMENT_ADVICE", ["investment_conclusion: NOT_INVESTMENT_ADVICE", "advice_status: NOT_INVESTMENT_ADVICE", "`NOT_INVESTMENT_ADVICE`"]),
    ]
    for label, markers in marker_groups:
        if not any(token in text for token in markers):
            raise RuntimeError(f"sector_card missing no-advice marker group: {label}")

    return {"source": source, "target": target, "source_rows": source_rows}


def _publish_sector_card_only(
    *,
    project_id: str,
    sector_id: str,
    config: ProjectConfig,
    manifest_path: Path,
    manifest: dict[str, Any],
    no_overwrite: bool,
) -> Path:
    checked = _assert_confirm_publish_allowed(
        config=config,
        project_id=project_id,
        sector_id=sector_id,
        manifest=manifest,
        publish_scope=SECTOR_CARD_ONLY,
        no_overwrite=no_overwrite,
    )
    source: Path = checked["source"]
    target: Path = checked["target"]
    source_rows: dict[str, dict[str, Any]] = checked["source_rows"]
    excluded_rows: dict[str, dict[str, Any]] = manifest.get("excluded_outputs_read_only", {}) or {}

    disallowed_before: dict[str, dict[str, Any]] = {}
    for output_type, row in excluded_rows.items():
        disallowed_before[output_type] = _snapshot_path(Path(row.get("target_path", "")))

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and no_overwrite:
        raise RuntimeError(f"target sector card already exists and --no-overwrite is active: {target}")
    shutil.copyfile(source, target)

    source_hash = _sha256(source)
    target_hash = _sha256(target)
    if source_hash != target_hash:
        raise RuntimeError("published sector_card hash does not match gated source hash")

    disallowed_after: dict[str, dict[str, Any]] = {}
    unchanged = True
    for output_type, row in excluded_rows.items():
        after = _snapshot_path(Path(row.get("target_path", "")))
        before = disallowed_before.get(output_type, {})
        disallowed_after[output_type] = after
        if before != after:
            unchanged = False

    log_path = default_publish_log_path(project_id, sector_id, manifest.get("run_id"))
    publish_log = {
        "project_id": project_id,
        "sector_id": sector_id,
        "publish_scope": SECTOR_CARD_ONLY,
        "release_manifest": str(manifest_path),
        "source_stage": manifest.get("source_stage", SOURCE_STAGE_GATED),
        "source_file": str(source),
        "source_gated_file": str(source),
        "source_candidate_file": str(source) if manifest.get("source_stage") == SOURCE_STAGE_CANDIDATE else "",
        "target_formal_file": str(target),
        "source_hash": source_hash,
        "target_hash": target_hash,
        "file_size": target.stat().st_size,
        "publish_time": _now_iso(),
        "confirm_publish": True,
        "overwrite": False,
        "gates_passed": True,
        "investment_advice": False,
        "score_status": "score_placeholder_not_applicable",
        "forbidden_artifacts_created": False,
        "published_files": {"sector_card": str(target)},
        "published_file_count": 1,
        "published_file_types": ["sector_card"],
        "skipped_outputs": {
            output_type: {
                "target_path": excluded_rows[output_type].get("target_path"),
                "before": disallowed_before.get(output_type),
                "after": disallowed_after.get(output_type),
                "unchanged": disallowed_before.get(output_type) == disallowed_after.get(output_type),
            }
            for output_type in sorted(disallowed_before)
        },
        "non_sector_outputs_unchanged": unchanged,
    }
    log_path.write_text(json.dumps(publish_log, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest.update(
        {
            "stage": "formal_publish_sector_card_only",
            "dry_run": False,
            "confirm_publish_requested": True,
            "confirm_publish_supported_in_this_phase": True,
            "publish_executed": True,
            "manual_confirmation_required": False,
            "publish_status": PUBLISHED_STATUS,
            "publish_scope": SECTOR_CARD_ONLY,
            "publish_log_path": str(log_path),
            "published_files": {"sector_card": str(target)},
        }
    )
    manifest.setdefault("gate_status", {})["publish_allowed_after_manual_confirmation"] = True
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return log_path


def build_release_manifest(
    project_id: str,
    sector_id: str,
    *,
    gated_root_arg: str | None = None,
    manifest_arg: str | None = None,
    dry_run: bool = True,
    confirm_publish: bool = False,
    publish_scope: str = REHEARSAL_SCOPE,
    write_manifest: bool = True,
) -> tuple[Path, dict[str, Any]]:
    config = load_project(project_id, create_dirs=False, strict=False, silent=True)
    gated_root = _resolve_root(gated_root_arg, get_gated_formal_output_dir(config))
    candidate_root = get_formal_candidate_output_dir(config).resolve()
    source_stage = SOURCE_STAGE_GATED
    try:
        metadata_path = _latest_gated_metadata(gated_root, sector_id)
    except FileNotFoundError:
        metadata_path = _latest_candidate_metadata(candidate_root, sector_id)
        source_stage = SOURCE_STAGE_CANDIDATE
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata_errors = _check_gated_metadata(metadata) if source_stage == SOURCE_STAGE_GATED else _check_candidate_metadata(metadata)
    source_files = (
        metadata.get("gated_formal_files", {}) or {}
        if source_stage == SOURCE_STAGE_GATED
        else metadata.get("formal_candidate_files", {}) or {"sector_card": str(get_candidate_paths(config, sector_id, metadata.get("run_id")).sector_card)}
    )
    all_final_paths = resolve_final_publish_paths(config, sector_id, metadata.get("run_id"))
    output_types = _publish_output_types(publish_scope)
    final_paths = {output_type: all_final_paths[output_type] for output_type in output_types}
    excluded_outputs = {
        output_type: {
            "target_path": target_path,
            "publish_action": False,
            "reason": f"excluded_by_publish_scope:{publish_scope}",
        }
        for output_type, target_path in all_final_paths.items()
        if output_type not in final_paths
    }

    if source_stage == SOURCE_STAGE_GATED:
        gate_findings, gate_summary = audit_gated_project(project_id, sector_id, write_report=True)
        gate_errors = [f"{f.code}: {f.message}" for f in gate_findings if f.severity == "ERROR"]
    else:
        candidate_gate = metadata.get("candidate_gate") or {}
        gate_errors = [f"candidate metadata: {err}" for err in metadata_errors]
        gate_summary = {
            "ERROR": candidate_gate.get("error_count", 1),
            "WARNING": candidate_gate.get("warning_count", 0),
            "source_id_closure": candidate_gate.get("status") == "PASS",
            "evidence_id_closure": candidate_gate.get("status") == "PASS",
            "no_investment_conclusion": candidate_gate.get("status") == "PASS",
            "score_placeholder": True,
            "formal_directory_pollution": metadata.get("formal_output_root_written") is False,
            "validate_outputs_exit_code": candidate_gate.get("validate_outputs_exit_code", 0),
        }

    file_records: list[dict[str, Any]] = []
    file_errors: list[str] = []
    for output_type in output_types:
        raw_source = source_files.get(output_type)
        if not raw_source:
            file_errors.append(f"gated metadata missing {output_type}")
            continue
        source = Path(raw_source)
        if not source.exists():
            file_errors.append(f"gated source missing {output_type}: {source}")
            continue
        target = Path(final_paths[output_type])
        file_records.append(
            _source_record(
                output_type=output_type,
                source_path=source,
                target_path=target,
                gated_root=gated_root,
                candidate_root=candidate_root,
            )
        )

    manifest_path = _resolve_root(manifest_arg, default_manifest_path(project_id, sector_id))
    if str(manifest_path.resolve()).startswith(str(config.output_root.resolve())):
        raise RuntimeError("release manifest path resolves inside final formal output root; refusing")

    target_overwrite_risk = any(row.get("overwrite_risk") for row in file_records)
    all_sources_from_gated = all(row.get("source_from_gated_staging") for row in file_records) and bool(file_records)
    all_sources_from_candidate = all(row.get("source_from_candidate_staging") for row in file_records) and bool(file_records)
    source_stage_ok = all_sources_from_gated if source_stage == SOURCE_STAGE_GATED else all_sources_from_candidate
    gates_passed = (
        gate_summary.get("ERROR") == 0
        and gate_summary.get("source_id_closure") is True
        and gate_summary.get("evidence_id_closure") is True
        and gate_summary.get("no_investment_conclusion") is True
        and gate_summary.get("score_placeholder") is True
        and gate_summary.get("formal_directory_pollution") is True
        and not metadata_errors
        and not file_errors
        and source_stage_ok
    )

    confirm_publish_supported = bool(confirm_publish and publish_scope == SECTOR_CARD_ONLY)
    publish_executed = False
    publish_allowed = bool(gates_passed and not target_overwrite_risk)
    if confirm_publish:
        publish_allowed = bool(confirm_publish_supported and gates_passed and not target_overwrite_risk)

    manifest = {
        "project_id": project_id,
        "sector_id": sector_id,
        "created_at": _now_iso(),
        "stage": "formal_publish_readiness_rehearsal",
        "publish_scope": publish_scope,
        "dry_run": bool(dry_run or not confirm_publish),
        "confirm_publish_requested": bool(confirm_publish),
        "confirm_publish_supported_in_this_phase": confirm_publish_supported,
        "publish_executed": publish_executed,
        "manual_confirmation_required": True,
        "publish_status": PUBLISH_STATUS,
        "source_stage": source_stage,
        "source_root": str(gated_root if source_stage == SOURCE_STAGE_GATED else candidate_root),
        "gated_formal_root": str(gated_root),
        "formal_candidate_root": str(candidate_root),
        "gated_metadata_path": str(metadata_path),
        "source_metadata_path": str(metadata_path),
        "release_manifest_path": str(manifest_path),
        "formal_target_paths_read_only": final_paths,
        "excluded_outputs_read_only": excluded_outputs,
        "file_map": file_records,
        "gate_status": {
            "gated_formal_audit_error_count": gate_summary.get("ERROR"),
            "gated_formal_audit_warning_count": gate_summary.get("WARNING"),
            "source_id_closure": gate_summary.get("source_id_closure"),
            "evidence_id_closure": gate_summary.get("evidence_id_closure"),
            "no_investment_conclusion": gate_summary.get("no_investment_conclusion"),
            "score_placeholder": gate_summary.get("score_placeholder"),
            "formal_directory_pollution": gate_summary.get("formal_directory_pollution"),
            "validate_outputs_exit_code": gate_summary.get("validate_outputs_exit_code"),
            "metadata_errors": metadata_errors,
            "file_errors": file_errors,
            "all_sources_from_gated_staging": all_sources_from_gated,
            "all_sources_from_candidate_staging": all_sources_from_candidate,
            "candidate_gate_error_count": gate_summary.get("ERROR") if source_stage == SOURCE_STAGE_CANDIDATE else None,
            "candidate_gate_warning_count": gate_summary.get("WARNING") if source_stage == SOURCE_STAGE_CANDIDATE else None,
            "target_overwrite_risk": target_overwrite_risk,
            "gates_passed": gates_passed,
            "publish_allowed_after_manual_confirmation": publish_allowed,
        },
        "future_confirm_publish_policy": {
            "requires_explicit_confirm_publish": True,
            "requires_gated_formal_audit_error_zero": True,
            "requires_no_investment_conclusion": True,
            "requires_score_placeholder_or_separate_scoring_gate": True,
            "requires_source_evidence_closure": True,
            "requires_release_manifest": True,
            "refuse_non_sector_overwrite": True,
            "refuse_unexpected_final_output_writes": True,
        },
    }
    if write_manifest:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path, manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare or execute a tightly scoped formal publish.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--sector-id", required=True)
    parser.add_argument("--gated-root", default=None)
    parser.add_argument("--release-manifest", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm-publish", action="store_true")
    parser.add_argument("--publish-scope", choices=[SECTOR_CARD_ONLY, REHEARSAL_SCOPE], default=REHEARSAL_SCOPE)
    parser.add_argument("--no-overwrite", action="store_true")
    args = parser.parse_args(argv)

    dry_run = True if not args.confirm_publish else args.dry_run
    if args.confirm_publish:
        readiness_exit, readiness_output = _run_readiness_audit(args.project, args.sector_id, args.release_manifest)
        if readiness_exit != 0:
            print("ERROR: publish readiness audit did not pass before confirmed publish.")
            print(readiness_output)
            return 1
    try:
        manifest_path, manifest = build_release_manifest(
            args.project,
            args.sector_id,
            gated_root_arg=args.gated_root,
            manifest_arg=args.release_manifest,
            dry_run=dry_run,
            confirm_publish=args.confirm_publish,
            publish_scope=args.publish_scope,
            write_manifest=True,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    if args.confirm_publish:
        try:
            config = load_project(args.project, create_dirs=False, strict=False, silent=True)
            publish_log = _publish_sector_card_only(
                project_id=args.project,
                sector_id=args.sector_id,
                config=config,
                manifest_path=manifest_path,
                manifest=manifest,
                no_overwrite=args.no_overwrite,
            )
        except Exception as exc:
            print(f"ERROR: {exc}")
            print(f"release_manifest: {manifest_path}")
            return 1
        target = manifest.get("published_files", {}).get("sector_card") or manifest.get("formal_target_paths_read_only", {}).get("sector_card")
        print("Formal publish complete")
        print(f"project_id: {manifest['project_id']}")
        print(f"sector_id: {manifest['sector_id']}")
        print(f"publish_scope: {args.publish_scope}")
        print(f"published: sector_card: {target}")
        print(f"publish_log: {publish_log}")
        print(f"release_manifest: {manifest_path}")
        return 0

    gate_status = manifest.get("gate_status", {})
    print("Formal publish readiness rehearsal complete")
    print(f"project_id: {manifest['project_id']}")
    print(f"sector_id: {manifest['sector_id']}")
    print(f"dry_run: {manifest['dry_run']}")
    print(f"publish_executed: {manifest['publish_executed']}")
    print(f"manual_confirmation_required: {manifest['manual_confirmation_required']}")
    print(f"release_manifest: {manifest_path}")
    print(f"gates_passed: {gate_status.get('gates_passed')}")
    print(f"publish_allowed_after_manual_confirmation: {gate_status.get('publish_allowed_after_manual_confirmation')}")
    print(f"target_overwrite_risk: {gate_status.get('target_overwrite_risk')}")
    for output_type, target in manifest["formal_target_paths_read_only"].items():
        print(f"target: {output_type}: {target}")
    return 0 if gate_status.get("gates_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
