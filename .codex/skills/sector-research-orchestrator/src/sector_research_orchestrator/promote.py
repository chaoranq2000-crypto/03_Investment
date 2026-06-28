"""Promote formal-candidate outputs into gated formal staging.

This script is a publication-prep gate only. It never writes to the final
formal output root and keeps all promoted files under project audits.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quality_auditor.candidate_outputs import audit_project
from research_writer.candidate_outputs import (
    CANDIDATE_STATUS,
    NO_ADVICE,
    NOT_RATED,
    get_formal_candidate_output_dir,
)
from investment_system.core.project_loader import (
    WORKSPACE_ROOT,
    ProjectConfig,
    load_project,
    resolve_output_path,
)


GATED_STATUS = "FORMAL_GATED_REVIEW_ONLY"
REQUIRED_OUTPUTS = [
    "sector_card",
    "company_table",
    "sector_comparison_table",
    "source_index",
    "missing_data_log",
    "conflict_data_log",
    "score_table",
]
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


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_gated_formal_output_dir(config: ProjectConfig) -> Path:
    return (
        WORKSPACE_ROOT
        / "investment_system"
        / "research"
        / "projects"
        / config.project_id
        / "audits"
        / "gated_formal_outputs"
    )


def _resolve_root(config: ProjectConfig, raw: str | None, default: Path) -> Path:
    if not raw:
        return default
    path = Path(raw)
    return path if path.is_absolute() else WORKSPACE_ROOT / path


def _assert_staging_path(config: ProjectConfig, output_root: Path, path: Path) -> None:
    target = path.resolve()
    root = output_root.resolve()
    formal_root = config.output_root.resolve()
    legacy_root = (WORKSPACE_ROOT / "科技主线调研输出").resolve()
    if not str(target).startswith(str(root)):
        raise RuntimeError(f"gated output path outside requested output_root: {target}")
    if str(target).startswith(str(formal_root)) or str(target).startswith(str(legacy_root)):
        raise RuntimeError(f"gated output path would write to formal output root: {target}")


def _load_candidate_metadata(candidate_root: Path, sector_id: str) -> tuple[Path, dict[str, Any]]:
    matches = sorted(candidate_root.glob(f"formal_candidate_{sector_id}_*_metadata.json"))
    if not matches:
        raise FileNotFoundError(f"No formal candidate metadata found for {sector_id} in {candidate_root}")
    path = matches[-1]
    return path, json.loads(path.read_text(encoding="utf-8"))


def _validate_candidate_integrity(metadata_path: Path, metadata: dict[str, Any], sector_id: str) -> list[str]:
    errors: list[str] = []
    if metadata.get("sector_id") != sector_id:
        errors.append(f"metadata sector_id mismatch: {metadata.get('sector_id')} != {sector_id}")
    if metadata.get("candidate_only") is not True:
        errors.append("metadata candidate_only is not true")
    if metadata.get("action_rating") != NOT_RATED:
        errors.append(f"metadata action_rating must be {NOT_RATED}")
    if metadata.get("suggested_action") != CANDIDATE_STATUS:
        errors.append(f"metadata suggested_action must be {CANDIDATE_STATUS}")
    if metadata.get("investment_conclusion") != NO_ADVICE:
        errors.append(f"metadata investment_conclusion must be {NO_ADVICE}")

    files = metadata.get("files", {}) or {}
    for output_type in REQUIRED_OUTPUTS:
        raw = files.get(output_type)
        if not raw:
            errors.append(f"metadata missing file entry: {output_type}")
            continue
        path = Path(raw)
        if not path.exists():
            errors.append(f"candidate file missing: {output_type}: {path}")
            continue
        name = path.name
        if "formal_candidate" not in name or sector_id not in name or not re.search(r"\d{8}", name):
            errors.append(f"candidate filename lacks required markers: {name}")

    shape = metadata.get("shape_validation", {}) or {}
    for output_type, result in shape.items():
        if result.get("errors"):
            errors.append(f"candidate shape errors for {output_type}: {result['errors']}")
    score_warnings = shape.get("score_table", {}).get("warnings", []) or []
    if not score_warnings:
        errors.append("score_table should still be placeholder/not_applicable in this phase")

    if not metadata_path.exists():
        errors.append(f"metadata file missing: {metadata_path}")
    return errors


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _validate_candidate_content(metadata: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    files = metadata.get("files", {}) or {}
    score_path = Path(files.get("score_table", ""))
    if score_path.exists():
        rows = _csv_rows(score_path)
        for row in rows:
            if row.get("rating") != NOT_RATED:
                errors.append("score_table rating is not NOT_RATED")
            if row.get("data_status") != "score_placeholder":
                errors.append("score_table data_status is not score_placeholder")
            score_values = [
                row.get("prosperity_score"),
                row.get("earnings_certainty_score"),
                row.get("valuation_score"),
                row.get("trading_comfort_score"),
                row.get("catalyst_score"),
                row.get("purity_score"),
                row.get("risk_control_score"),
                row.get("total_score"),
            ]
            if any(value != "not_applicable" for value in score_values):
                errors.append("score_table contains non-placeholder score values")

    for output_type, raw in files.items():
        path = Path(raw)
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8-sig", errors="ignore")
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(content):
                errors.append(f"{output_type} contains forbidden investment wording: {pattern.pattern}")
    return errors


def _gated_path(output_root: Path, candidate_path: Path) -> Path:
    name = candidate_path.name.replace("formal_candidate", "gated_formal")
    return output_root / name


def _promoted_text(text: str) -> str:
    return (
        text.replace(CANDIDATE_STATUS, GATED_STATUS)
        .replace("formal_candidate", "gated_formal")
        .replace("Formal candidate", "Gated formal")
        .replace("formal candidate", "gated formal")
    )


def _future_formal_paths(config: ProjectConfig, sector_id: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for output_type in [
        "sector_card",
        "company_table",
        "sector_comparison_table",
        "source_index",
        "missing_data_log",
        "conflict_data_log",
        "score_table",
    ]:
        try:
            result[output_type] = resolve_output_path(config, output_type, sector_id if output_type == "sector_card" else None)
        except Exception as exc:
            result[output_type] = f"(unresolved: {exc})"
    return result


def promote(
    project_id: str,
    sector_id: str,
    *,
    candidate_root_arg: str | None = None,
    output_root_arg: str | None = None,
    clean: bool = False,
    require_audit_pass: bool = False,
) -> dict[str, Any]:
    config = load_project(project_id, create_dirs=False, strict=False, silent=True)
    candidate_root = _resolve_root(config, candidate_root_arg, get_formal_candidate_output_dir(config))
    output_root = _resolve_root(config, output_root_arg, get_gated_formal_output_dir(config))
    if str(output_root.resolve()).startswith(str(config.output_root.resolve())):
        raise RuntimeError("output_root resolves inside final formal output root; refusing promotion")

    candidate_audit_summary: dict[str, Any] = {}
    if require_audit_pass:
        _findings, candidate_audit_summary = audit_project(project_id, sector_id, write_report=True)
        if candidate_audit_summary.get("ERROR"):
            raise RuntimeError(f"formal candidate audit did not pass: ERROR={candidate_audit_summary.get('ERROR')}")
        if not candidate_audit_summary.get("source_id_closure") or not candidate_audit_summary.get("evidence_id_closure"):
            raise RuntimeError("formal candidate source/evidence closure did not pass")
        if candidate_audit_summary.get("shape_errors"):
            raise RuntimeError(f"formal candidate shape_errors={candidate_audit_summary.get('shape_errors')}")

    metadata_path, metadata = _load_candidate_metadata(candidate_root, sector_id)
    errors = _validate_candidate_integrity(metadata_path, metadata, sector_id)
    errors.extend(_validate_candidate_content(metadata))
    if errors:
        raise RuntimeError("candidate integrity check failed: " + "; ".join(errors))

    output_root.mkdir(parents=True, exist_ok=True)
    files = metadata.get("files", {}) or {}
    promoted_files: dict[str, str] = {}
    for output_type in REQUIRED_OUTPUTS:
        source = Path(files[output_type])
        target = _gated_path(output_root, source)
        _assert_staging_path(config, output_root, target)
        if clean and target.exists():
            target.unlink()
        content = source.read_text(encoding="utf-8-sig", errors="ignore")
        target.write_text(_promoted_text(content), encoding="utf-8")
        promoted_files[output_type] = str(target)

    gated_metadata_path = output_root / metadata_path.name.replace("formal_candidate", "gated_formal")
    _assert_staging_path(config, output_root, gated_metadata_path)
    if clean and gated_metadata_path.exists():
        gated_metadata_path.unlink()
    gated_metadata = {
        "project_id": project_id,
        "sector_id": sector_id,
        "run_id": metadata.get("run_id"),
        "promotion_time": _now_iso(),
        "stage": "gated_formal_staging",
        "candidate_metadata_path": str(metadata_path),
        "candidate_root": str(candidate_root),
        "gated_formal_root": str(output_root),
        "candidate_audit": candidate_audit_summary,
        "source_candidate_files": files,
        "gated_formal_files": promoted_files,
        "action_rating": NOT_RATED,
        "suggested_action": GATED_STATUS,
        "investment_conclusion": NO_ADVICE,
        "score_status": "score_placeholder_not_applicable",
        "future_formal_publish_paths_read_only": _future_formal_paths(config, sector_id),
    }
    gated_metadata_path.write_text(json.dumps(gated_metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    promoted_files["metadata"] = str(gated_metadata_path)
    return {
        "project_id": project_id,
        "sector_id": sector_id,
        "candidate_root": str(candidate_root),
        "gated_formal_root": str(output_root),
        "candidate_metadata": str(metadata_path),
        "gated_metadata": str(gated_metadata_path),
        "promoted_files": promoted_files,
        "candidate_audit_error_count": candidate_audit_summary.get("ERROR", 0),
        "source_id_closure": candidate_audit_summary.get("source_id_closure", True),
        "evidence_id_closure": candidate_audit_summary.get("evidence_id_closure", True),
        "score_status": "score_placeholder_not_applicable",
        "future_formal_publish_paths_read_only": gated_metadata["future_formal_publish_paths_read_only"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Promote formal candidate outputs into gated formal staging.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--sector-id", required=True)
    parser.add_argument("--candidate-root", default=None)
    parser.add_argument("--output-root", default=None)
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--require-audit-pass", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = promote(
            args.project,
            args.sector_id,
            candidate_root_arg=args.candidate_root,
            output_root_arg=args.output_root,
            clean=args.clean,
            require_audit_pass=args.require_audit_pass,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print("Formal candidate promoted to gated formal staging")
    print(f"project_id: {result['project_id']}")
    print(f"sector_id: {result['sector_id']}")
    print(f"candidate_root: {result['candidate_root']}")
    print(f"gated_formal_root: {result['gated_formal_root']}")
    print(f"candidate_audit_error_count: {result['candidate_audit_error_count']}")
    print(f"source_id_closure: {result['source_id_closure']}")
    print(f"evidence_id_closure: {result['evidence_id_closure']}")
    print(f"score_status: {result['score_status']}")
    for output_type, path in result["promoted_files"].items():
        print(f"wrote: {output_type}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
