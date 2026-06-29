"""Audit project-aware evidence bindings for a sector research project.

This audit validates only evidence indexing and binding metadata. It does not
read evidence YAML contents, does not generate research output, and does not use
seed documents or retired outputs as active evidence.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from investment_system.core.project_loader import (
    WORKSPACE_ROOT,
    load_project,
    resolve_evidence_files_for_sector,
)


@dataclass
class Finding:
    severity: str
    code: str
    message: str


def _path(raw_path: str) -> Path:
    p = Path(raw_path)
    return p if p.is_absolute() else WORKSPACE_ROOT / p


def _sector_required(sector: dict[str, Any]) -> bool:
    return (
        bool(sector.get("scoring_enabled", False))
        and str(sector.get("priority", "")).upper() in {"P0", "P1"}
    )


def _manifest_sector_ids(ef: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    sid = str(ef.get("sector_id", "") or "")
    if sid:
        ids.add(sid)
    for key in ("sector_ids", "sectors"):
        raw = ef.get(key, []) or []
        if isinstance(raw, str):
            ids.add(raw)
        else:
            ids.update(str(item) for item in raw if item)
    return ids


def audit_project(project_id: str) -> tuple[list[Finding], dict[str, Any]]:
    config = load_project(project_id, silent=True, strict=False)
    sectors = config.raw.get("sectors", [])
    sector_ids = {s.get("sector_id") for s in sectors if s.get("sector_id")}
    evidence_files = config.raw.get("evidence_files", [])
    manifest = config.raw.get("run_manifest", {})
    seed_docs = manifest.get("seed_documents", []) or []
    retired_outputs = config.raw.get("retired_outputs", [])
    findings: list[Finding] = []

    ef_id_to_manifest: dict[str, dict[str, Any]] = {}
    duplicate_ids: set[str] = set()
    for ef in evidence_files:
        ef_id = str(ef.get("evidence_file_id", "") or "")
        if not ef_id:
            findings.append(Finding("ERROR", "EVIDENCE_FILE_ID_MISSING", "evidence_files[] entry missing evidence_file_id."))
            continue
        if ef_id in ef_id_to_manifest:
            duplicate_ids.add(ef_id)
        ef_id_to_manifest[ef_id] = ef

    for ef_id in sorted(duplicate_ids):
        findings.append(Finding("ERROR", "EVIDENCE_FILE_ID_DUPLICATE", f"duplicate evidence_file_id: {ef_id}"))

    sector_ref_ids: dict[str, set[str]] = {}
    for sector in sectors:
        sid = sector.get("sector_id", "")
        for ef_id in sector.get("evidence_file_ids", []) or []:
            refs = sector_ref_ids.setdefault(ef_id, set())
            if refs and sid not in refs:
                manifest_ref = ef_id_to_manifest.get(ef_id, {})
                allowed_refs = _manifest_sector_ids(manifest_ref)
                proposed_refs = set(refs)
                proposed_refs.add(sid)
                if not proposed_refs.issubset(allowed_refs):
                    findings.append(
                        Finding(
                            "ERROR",
                            "EVIDENCE_FILE_ID_MULTI_BOUND",
                            f"evidence_file_id '{ef_id}' referenced by both {sorted(refs)} and {sid}.",
                        )
                    )
            refs.add(sid)
            if ef_id not in ef_id_to_manifest:
                findings.append(
                    Finding(
                        "ERROR",
                        "SECTOR_EVIDENCE_ID_NOT_IN_MANIFEST",
                        f"sector {sid} references evidence_file_id '{ef_id}' not found in run_manifest.yaml.",
                    )
                )

    seed_paths = {_path(str(sd.get("path", ""))).resolve() for sd in seed_docs if sd.get("path")}
    retired_paths = {_path(str(ro.get("path", ""))).resolve() for ro in retired_outputs if ro.get("path")}

    for ef in evidence_files:
        ef_id = str(ef.get("evidence_file_id", "") or "")
        raw_path = str(ef.get("path", "") or "")
        sid = str(ef.get("sector_id", "") or "")
        ef_path = _path(raw_path).resolve() if raw_path else WORKSPACE_ROOT

        if not raw_path:
            findings.append(Finding("ERROR", "EVIDENCE_PATH_MISSING", f"evidence_file_id '{ef_id}' missing path."))
        elif not ef_path.exists():
            findings.append(Finding("WARNING", "EVIDENCE_PATH_NOT_FOUND", f"evidence file path does not exist: {raw_path}"))

        if sid not in sector_ids:
            findings.append(
                Finding("ERROR", "EVIDENCE_SECTOR_ID_INVALID", f"evidence_file_id '{ef_id}' has invalid sector_id '{sid}'.")
            )

        allowed_refs = _manifest_sector_ids(ef)
        refs = sector_ref_ids.get(ef_id, set())
        if ef_id and refs and not refs.issubset(allowed_refs):
            findings.append(
                Finding(
                    "ERROR",
                    "EVIDENCE_FILE_ID_SECTOR_MISMATCH",
                    f"evidence_file_id '{ef_id}' bound to {sorted(allowed_refs)} but sector_universe references {sorted(refs)}.",
                )
            )
        elif ef_id and not refs:
            findings.append(
                Finding(
                    "ERROR",
                    "EVIDENCE_FILE_ID_UNBOUND",
                    f"evidence_file_id '{ef_id}' is not referenced by any sector_universe evidence_file_ids.",
                )
            )

        if ef_path in seed_paths:
            findings.append(Finding("ERROR", "SEED_DOCUMENT_AS_EVIDENCE", f"seed document reused as evidence: {raw_path}"))
        if ef_path in retired_paths:
            findings.append(Finding("ERROR", "RETIRED_OUTPUT_AS_EVIDENCE", f"retired output reused as active evidence: {raw_path}"))

    coverage: list[dict[str, Any]] = []
    for sector in sectors:
        sid = sector.get("sector_id", "")
        records = resolve_evidence_files_for_sector(config, sid)
        status = "ok" if records else "missing"
        coverage.append(
            {
                "sector_id": sid,
                "priority": sector.get("priority", ""),
                "scoring_enabled": sector.get("scoring_enabled", False),
                "evidence_count": len(records),
                "coverage_status": status,
                "evidence_file_ids": [r.get("evidence_file_id", "") for r in records],
            }
        )
        if not records:
            if _sector_required(sector):
                findings.append(
                    Finding(
                        "WARNING",
                        "P0_P1_EVIDENCE_MISSING",
                        f"{sector.get('priority')} scoring sector '{sid}' has no bound evidence yet.",
                    )
                )
            else:
                findings.append(Finding("INFO", "SECTOR_EVIDENCE_MISSING", f"sector '{sid}' has no bound evidence yet."))

    evidence_overrides = WORKSPACE_ROOT / "investment_system" / "pipelines" / "evidence_overrides.py"
    if evidence_overrides.exists():
        findings.append(
            Finding(
                "ERROR",
                "REMOVED_EVIDENCE_OVERRIDES_PRESENT",
                "evidence_overrides.py is no longer an allowed runtime surface.",
            )
        )
    else:
        findings.append(
            Finding(
                "INFO",
                "EVIDENCE_OVERRIDES_RETIRED",
                "evidence_overrides.py is not present; project-aware evidence uses project manifests.",
            )
        )

    summary = {
        "project_id": config.project_id,
        "evidence_file_count": len(evidence_files),
        "sector_count": len(sectors),
        "coverage": coverage,
        "duplicate_ids": sorted(duplicate_ids),
        "manifest_ids": sorted(ef_id_to_manifest),
        "sector_ref_ids": {key: sorted(value) for key, value in sorted(sector_ref_ids.items())},
    }
    return findings, summary


def _print_report(findings: list[Finding], summary: dict[str, Any]) -> None:
    error_count = sum(1 for f in findings if f.severity == "ERROR")
    warning_count = sum(1 for f in findings if f.severity == "WARNING")
    info_count = sum(1 for f in findings if f.severity == "INFO")

    print("Evidence Binding Audit")
    print("=" * 60)
    print(f"project_id          : {summary['project_id']}")
    print(f"evidence_file_count : {summary['evidence_file_count']}")
    print(f"sector_count        : {summary['sector_count']}")
    print(f"ERROR               : {error_count}")
    print(f"WARNING             : {warning_count}")
    print(f"INFO                : {info_count}")
    print()

    print("Evidence files")
    for ef_id in summary["manifest_ids"]:
        sector = summary["sector_ref_ids"].get(ef_id, "(not referenced)")
        print(f"  - {ef_id}: sector_ref={sector}")
    print()

    print("Sector evidence coverage")
    for row in summary["coverage"]:
        ids = ", ".join(row["evidence_file_ids"]) if row["evidence_file_ids"] else "-"
        print(
            f"  - {row['sector_id']}: {row['coverage_status']} "
            f"(priority={row['priority']}, scoring={row['scoring_enabled']}, "
            f"count={row['evidence_count']}, ids={ids})"
        )
    print()

    for severity in ["ERROR", "WARNING", "INFO"]:
        rows = [f for f in findings if f.severity == severity]
        if not rows:
            continue
        print(f"{severity}s")
        for f in rows:
            print(f"  [{f.code}] {f.message}")
        print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit project-aware evidence bindings.")
    parser.add_argument("--project", required=True, help="Project ID under research/projects/")
    args = parser.parse_args(argv)

    findings, summary = audit_project(args.project)
    _print_report(findings, summary)
    return 1 if any(f.severity == "ERROR" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
