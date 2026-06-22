"""Prepare a dry-run release manifest for final formal publication.

The default behavior is rehearsal only: resolve final project-aware output
paths, verify gated formal staging, and write a release manifest under audits.
No files are copied to the final formal output root unless a future phase
implements and explicitly enables confirmed publication.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from investment_system.pipelines.sector_research.audit_gated_formal_outputs import audit_project
from investment_system.pipelines.sector_research.load_project import (
    WORKSPACE_ROOT,
    ProjectConfig,
    load_project,
    resolve_output_path,
)
from investment_system.pipelines.sector_research.promote_formal_candidate_outputs import (
    GATED_STATUS,
    NO_ADVICE,
    NOT_RATED,
    REQUIRED_OUTPUTS,
    get_gated_formal_output_dir,
)


MANIFEST_PREFIX = "formal_publish_manifest"
PUBLISH_STATUS = "awaiting_manual_confirmation"


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


def _latest_gated_metadata(gated_root: Path, sector_id: str) -> Path:
    matches = sorted(gated_root.glob(f"gated_formal_{sector_id}_*_metadata.json"))
    if not matches:
        raise FileNotFoundError(f"No gated formal metadata found for {sector_id} in {gated_root}")
    return matches[-1]


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


def _source_record(
    *,
    output_type: str,
    source_path: Path,
    target_path: Path,
    gated_root: Path,
) -> dict[str, Any]:
    target_exists = target_path.exists()
    shared_target = output_type in {
        "company_table",
        "sector_comparison_table",
        "source_index",
        "missing_data_log",
        "conflict_data_log",
        "score_table",
        "release_manifest",
    }
    return {
        "output_type": output_type,
        "source_path": str(source_path),
        "source_from_gated_staging": str(source_path.resolve()).startswith(str(gated_root.resolve())),
        "target_path": str(target_path),
        "target_exists": target_exists,
        "write_mode_if_confirmed_future": "append_or_merge" if shared_target else "create_or_replace_same_sector_only",
        "overwrite_risk": bool(target_exists and not shared_target),
        "non_sector_overwrite_risk": False,
        "sha256": _sha256(source_path),
        "size_bytes": source_path.stat().st_size,
    }


def build_release_manifest(
    project_id: str,
    sector_id: str,
    *,
    gated_root_arg: str | None = None,
    manifest_arg: str | None = None,
    dry_run: bool = True,
    confirm_publish: bool = False,
    write_manifest: bool = True,
) -> tuple[Path, dict[str, Any]]:
    config = load_project(project_id, create_dirs=False, strict=False, silent=True)
    gated_root = _resolve_root(gated_root_arg, get_gated_formal_output_dir(config))
    metadata_path = _latest_gated_metadata(gated_root, sector_id)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata_errors = _check_gated_metadata(metadata)
    gated_files = metadata.get("gated_formal_files", {}) or {}
    final_paths = resolve_final_publish_paths(config, sector_id, metadata.get("run_id"))

    gate_findings, gate_summary = audit_project(project_id, sector_id, write_report=True)
    gate_errors = [f"{f.code}: {f.message}" for f in gate_findings if f.severity == "ERROR"]

    file_records: list[dict[str, Any]] = []
    file_errors: list[str] = []
    for output_type in REQUIRED_OUTPUTS:
        raw_source = gated_files.get(output_type)
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
            )
        )

    manifest_path = _resolve_root(manifest_arg, default_manifest_path(project_id, sector_id))
    if str(manifest_path.resolve()).startswith(str(config.output_root.resolve())):
        raise RuntimeError("release manifest path resolves inside final formal output root; refusing")

    target_overwrite_risk = any(row.get("overwrite_risk") for row in file_records)
    all_sources_from_gated = all(row.get("source_from_gated_staging") for row in file_records) and bool(file_records)
    gates_passed = (
        gate_summary.get("ERROR") == 0
        and gate_summary.get("source_id_closure") is True
        and gate_summary.get("evidence_id_closure") is True
        and gate_summary.get("no_investment_conclusion") is True
        and gate_summary.get("score_placeholder") is True
        and gate_summary.get("formal_directory_pollution") is True
        and not metadata_errors
        and not file_errors
        and all_sources_from_gated
    )

    confirm_publish_supported = False
    publish_executed = False
    publish_allowed = bool(gates_passed and not target_overwrite_risk)
    if confirm_publish:
        publish_allowed = False

    manifest = {
        "project_id": project_id,
        "sector_id": sector_id,
        "created_at": _now_iso(),
        "stage": "formal_publish_readiness_rehearsal",
        "dry_run": bool(dry_run or not confirm_publish),
        "confirm_publish_requested": bool(confirm_publish),
        "confirm_publish_supported_in_this_phase": confirm_publish_supported,
        "publish_executed": publish_executed,
        "manual_confirmation_required": True,
        "publish_status": PUBLISH_STATUS,
        "gated_formal_root": str(gated_root),
        "gated_metadata_path": str(metadata_path),
        "release_manifest_path": str(manifest_path),
        "formal_target_paths_read_only": final_paths,
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
    parser = argparse.ArgumentParser(description="Prepare formal publish release manifest without publishing.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--sector-id", required=True)
    parser.add_argument("--gated-root", default=None)
    parser.add_argument("--release-manifest", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm-publish", action="store_true")
    args = parser.parse_args(argv)

    dry_run = True if not args.confirm_publish else args.dry_run
    try:
        manifest_path, manifest = build_release_manifest(
            args.project,
            args.sector_id,
            gated_root_arg=args.gated_root,
            manifest_arg=args.release_manifest,
            dry_run=dry_run,
            confirm_publish=args.confirm_publish,
            write_manifest=True,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    if args.confirm_publish:
        print("ERROR: --confirm-publish is intentionally not executable in phase 1E-h-c.")
        print(f"release_manifest: {manifest_path}")
        return 2

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
