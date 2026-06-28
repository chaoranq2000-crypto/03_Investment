"""Register a project-aware evidence YAML file for one canonical sector.

This is a narrow helper for the repeated evidence-registration step:

1. Add the evidence file to ``run_manifest.yaml`` under ``evidence_files``.
2. Add its ``evidence_file_id`` to exactly one sector's ``evidence_file_ids``.

The helper intentionally does not generate evidence content and does not touch
formal output directories.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from investment_system.pipelines.sector_research.load_project import (
    PROJECTS_ROOT,
    WORKSPACE_ROOT,
    get_sector,
    load_project,
)
from investment_system.pipelines.sector_research.validate_curated_evidence import validate_evidence_file


@dataclass
class RegistrationPlan:
    project_id: str
    sector_id: str
    evidence_file_id: str
    evidence_path: str
    manifest_path: Path
    sector_universe_path: Path
    manifest_action: str
    sector_action: str
    dry_run: bool


def _read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _as_workspace_relative(raw_path: str) -> str:
    path = Path(raw_path)
    if not path.is_absolute():
        return raw_path.replace("\\", "/")
    try:
        return path.resolve().relative_to(WORKSPACE_ROOT).as_posix()
    except ValueError as exc:
        raise ValueError(f"evidence path must be under workspace root: {path}") from exc


def _resolve_workspace_path(raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else WORKSPACE_ROOT / path


def _format_manifest_entry(
    *,
    path: str,
    evidence_type: str,
    sector_id: str,
    evidence_file_id: str,
    status: str,
    action: str,
    notes: str,
) -> str:
    lines = [
        f"  - path: {path}",
        f"    type: {evidence_type}",
        f"    sector_id: {sector_id}",
        f"    evidence_file_id: {evidence_file_id}",
        f"    status: {status}",
        f"    action: {action}",
    ]
    if notes:
        lines.append("    notes: >")
        for note_line in notes.splitlines() or [notes]:
            lines.append(f"      {note_line}")
    return "\n".join(lines) + "\n\n"


def _insert_manifest_entry(
    text: str,
    *,
    path: str,
    evidence_type: str,
    sector_id: str,
    evidence_file_id: str,
    status: str,
    action: str,
    notes: str,
) -> tuple[str, str]:
    data = yaml.safe_load(text) or {}
    existing = data.get("evidence_files", []) or []
    for row in existing:
        if row.get("evidence_file_id") == evidence_file_id:
            if row.get("sector_id") != sector_id:
                raise ValueError(
                    f"evidence_file_id '{evidence_file_id}' already exists for sector_id '{row.get('sector_id')}'."
                )
            return text, "already_present"

    marker = "# ── Seed Documents"
    index = text.find(marker)
    if index < 0:
        marker = "\nseed_documents:"
        index = text.find(marker)
    if index < 0:
        raise ValueError("cannot find insertion point before seed_documents in run_manifest.yaml")

    entry = _format_manifest_entry(
        path=path,
        evidence_type=evidence_type,
        sector_id=sector_id,
        evidence_file_id=evidence_file_id,
        status=status,
        action=action,
        notes=notes,
    )
    prefix = text[:index]
    suffix = text[index:]
    if not prefix.endswith("\n\n"):
        prefix = prefix.rstrip() + "\n\n"
    return prefix + entry + suffix, "add"


def _sector_blocks(lines: list[str]) -> list[tuple[int, int, str]]:
    starts: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("- sector_id: "):
            starts.append((i, stripped.split(":", 1)[1].strip()))
    blocks: list[tuple[int, int, str]] = []
    for pos, (start, sector_id) in enumerate(starts):
        end = starts[pos + 1][0] if pos + 1 < len(starts) else len(lines)
        blocks.append((start, end, sector_id))
    return blocks


def _sector_refs_evidence(block: list[str], evidence_file_id: str) -> bool:
    return any(line.strip() == f"- {evidence_file_id}" for line in block)


def _add_sector_binding(text: str, *, sector_id: str, evidence_file_id: str) -> tuple[str, str]:
    lines = text.splitlines()
    blocks = _sector_blocks(lines)

    other_refs = [
        sid for start, end, sid in blocks
        if sid != sector_id and _sector_refs_evidence(lines[start:end], evidence_file_id)
    ]
    if other_refs:
        raise ValueError(f"evidence_file_id '{evidence_file_id}' is already referenced by other sectors: {other_refs}")

    target = next(((start, end, sid) for start, end, sid in blocks if sid == sector_id), None)
    if target is None:
        raise ValueError(f"sector_id not found in sector_universe.yaml: {sector_id}")

    start, end, _sid = target
    block = lines[start:end]
    if _sector_refs_evidence(block, evidence_file_id):
        return text, "already_present"

    for offset, line in enumerate(block):
        if line.strip().startswith("evidence_file_ids:"):
            line_index = start + offset
            indent = line[: len(line) - len(line.lstrip())]
            if line.strip() == "evidence_file_ids: []":
                lines[line_index] = f"{indent}evidence_file_ids:"
                lines.insert(line_index + 1, f"{indent}  - {evidence_file_id}")
                return "\n".join(lines) + "\n", "add"

            insert_at = line_index + 1
            while insert_at < end and lines[insert_at].startswith(f"{indent}  - "):
                insert_at += 1
            lines.insert(insert_at, f"{indent}  - {evidence_file_id}")
            return "\n".join(lines) + "\n", "add"

    raise ValueError(f"sector block has no evidence_file_ids field: {sector_id}")


def build_registration_plan(
    *,
    project_id: str,
    sector_id: str,
    evidence_path: str,
    evidence_file_id: str | None,
    evidence_type: str,
    status: str,
    action: str,
    notes: str,
    allow_missing: bool,
    dry_run: bool,
) -> tuple[RegistrationPlan, str, str]:
    config = load_project(project_id, create_dirs=False, strict=False, silent=True)
    canonical_sector = get_sector(config, sector_id).get("sector_id", "")
    rel_path = _as_workspace_relative(evidence_path)
    resolved = _resolve_workspace_path(rel_path)
    if not resolved.exists() and not allow_missing:
        raise ValueError(f"evidence file does not exist: {rel_path}")
    if resolved.exists():
        findings = validate_evidence_file(resolved)
        errors = [f"{finding.code}: {finding.message}" for finding in findings if finding.severity == "ERROR"]
        if errors:
            raise ValueError("evidence file is not curated/registerable: " + "; ".join(errors))

    inferred_id = Path(rel_path).stem
    ef_id = evidence_file_id or inferred_id
    if not ef_id:
        raise ValueError("evidence_file_id is required when it cannot be inferred from the path")

    project_dir = PROJECTS_ROOT / project_id
    manifest_path = project_dir / "run_manifest.yaml"
    sector_path = project_dir / "sector_universe.yaml"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    sector_text = sector_path.read_text(encoding="utf-8")

    updated_manifest, manifest_action = _insert_manifest_entry(
        manifest_text,
        path=rel_path,
        evidence_type=evidence_type,
        sector_id=canonical_sector,
        evidence_file_id=ef_id,
        status=status,
        action=action,
        notes=notes,
    )
    updated_sector, sector_action = _add_sector_binding(
        sector_text,
        sector_id=canonical_sector,
        evidence_file_id=ef_id,
    )

    plan = RegistrationPlan(
        project_id=project_id,
        sector_id=canonical_sector,
        evidence_file_id=ef_id,
        evidence_path=rel_path,
        manifest_path=manifest_path,
        sector_universe_path=sector_path,
        manifest_action=manifest_action,
        sector_action=sector_action,
        dry_run=dry_run,
    )

    if not dry_run:
        if updated_manifest != manifest_text:
            manifest_path.write_text(updated_manifest, encoding="utf-8")
        if updated_sector != sector_text:
            sector_path.write_text(updated_sector, encoding="utf-8")

    return plan, updated_manifest, updated_sector


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Register one evidence YAML file for one canonical sector.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--sector-id", required=True)
    parser.add_argument("--path", required=True, help="Evidence YAML path, absolute or workspace-relative.")
    parser.add_argument("--evidence-file-id", default=None)
    parser.add_argument("--type", default="evidence_yaml")
    parser.add_argument("--status", default="schema_normalized")
    parser.add_argument("--action", default="index_only")
    parser.add_argument("--notes", default="")
    parser.add_argument("--allow-missing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        plan, _manifest_text, _sector_text = build_registration_plan(
            project_id=args.project,
            sector_id=args.sector_id,
            evidence_path=args.path,
            evidence_file_id=args.evidence_file_id,
            evidence_type=args.type,
            status=args.status,
            action=args.action,
            notes=args.notes,
            allow_missing=args.allow_missing,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print("Evidence registration plan")
    print(f"project_id: {plan.project_id}")
    print(f"sector_id: {plan.sector_id}")
    print(f"evidence_file_id: {plan.evidence_file_id}")
    print(f"evidence_path: {plan.evidence_path}")
    print(f"manifest_action: {plan.manifest_action}")
    print(f"sector_binding_action: {plan.sector_action}")
    print(f"dry_run: {plan.dry_run}")
    if plan.dry_run:
        print("no files written")
    else:
        print(f"updated: {plan.manifest_path}")
        print(f"updated: {plan.sector_universe_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
