"""Audit canonical evidence YAML schema/source_id readiness.

The audit reads active evidence files through load_project +
resolve_evidence_files_for_sector. It writes an engineering audit markdown file
under the project audits directory and does not generate research outputs.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from investment_system.pipelines.sector_research.load_project import (
    WORKSPACE_ROOT,
    get_sector,
    load_project,
    resolve_evidence_files_for_sector,
    resolve_sector_id,
)


REQUIRED_TOP_LEVEL = [
    "schema_version",
    "evidence_file_id",
    "status",
    "project_ids",
    "canonical_sector_ids",
    "source_index",
    "evidence_items",
]

LEGACY_TOP_LEVEL = {
    "sub_theme",
    "grade",
    "description",
    "company_overrides",
    "comparison_override",
    "source_rows",
    "logs",
    "card_markdown",
}


@dataclass
class Finding:
    severity: str
    code: str
    message: str
    file: str = ""


def _path(raw_path: str) -> Path:
    p = Path(raw_path)
    return p if p.is_absolute() else WORKSPACE_ROOT / p


def _active_evidence_records(config: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for sector in config.raw.get("sectors", []) or []:
        sid = sector.get("sector_id", "")
        if not sid:
            continue
        for rec in resolve_evidence_files_for_sector(config, sid):
            key = rec.get("evidence_file_id") or rec.get("path", "")
            if key in seen:
                continue
            seen.add(key)
            records.append(rec)
    return records


def _has_source_location(source: dict[str, Any]) -> bool:
    return bool(str(source.get("url", "")).strip() or str(source.get("path", "")).strip())


def _is_empty_source_metadata(source: dict[str, Any]) -> bool:
    return (
        not str(source.get("title", "")).strip()
        or not str(source.get("date", "")).strip()
        or not _has_source_location(source)
    )


def _load_yaml(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}, ""
    except Exception as exc:  # noqa: BLE001 - audit should capture parse errors
        return None, str(exc)


def audit_project(project_id: str, write_report: bool = True) -> tuple[list[Finding], dict[str, Any]]:
    config = load_project(project_id, silent=True, strict=False)
    sectors = config.raw.get("sectors", []) or []
    valid_sector_ids = {s.get("sector_id") for s in sectors if s.get("sector_id")}
    legacy_map = config.raw.get("legacy_sector_map", {})
    manifest = config.raw.get("run_manifest", {})
    seed_paths = {
        _path(str(row.get("path", ""))).resolve()
        for row in (manifest.get("seed_documents", []) or [])
        if row.get("path")
    }
    retired_paths = {
        _path(str(row.get("path", ""))).resolve()
        for row in (config.raw.get("retired_legacy_outputs", []) or [])
        if row.get("path")
    }

    findings: list[Finding] = []
    records = _active_evidence_records(config)
    file_summaries: list[dict[str, Any]] = []
    total_sources = 0
    total_items = 0
    missing_source_metadata_count = 0
    legacy_only_field_count = 0
    canonical_sector_binding_count = 0

    for rec in records:
        rel_path = str(rec.get("path", "") or "")
        ef_id = str(rec.get("evidence_file_id", "") or "")
        file_path = _path(rel_path).resolve()
        file_summary = {
            "evidence_file_id": ef_id,
            "path": rel_path,
            "source_count": 0,
            "evidence_item_count": 0,
            "canonical_sector_ids": [],
            "legacy_only_fields": [],
            "missing_source_metadata_count": 0,
        }

        if file_path in seed_paths:
            findings.append(Finding("ERROR", "SEED_DOCUMENT_AS_EVIDENCE", f"seed document registered as evidence: {rel_path}", rel_path))
        if file_path in retired_paths:
            findings.append(Finding("ERROR", "RETIRED_OUTPUT_AS_EVIDENCE", f"retired legacy output registered as active evidence: {rel_path}", rel_path))

        if not file_path.exists():
            findings.append(Finding("ERROR", "EVIDENCE_FILE_NOT_FOUND", f"active evidence YAML does not exist: {rel_path}", rel_path))
            file_summaries.append(file_summary)
            continue

        data, parse_error = _load_yaml(file_path)
        if data is None:
            findings.append(Finding("ERROR", "EVIDENCE_YAML_PARSE_ERROR", f"cannot parse YAML: {parse_error}", rel_path))
            file_summaries.append(file_summary)
            continue

        for key in REQUIRED_TOP_LEVEL:
            if key not in data:
                findings.append(Finding("ERROR", "EVIDENCE_SCHEMA_FIELD_MISSING", f"missing top-level field '{key}'", rel_path))

        if data.get("evidence_file_id") != ef_id:
            findings.append(
                Finding(
                    "ERROR",
                    "EVIDENCE_FILE_ID_MISMATCH",
                    f"YAML evidence_file_id='{data.get('evidence_file_id')}' does not match manifest id '{ef_id}'.",
                    rel_path,
                )
            )

        canonical_sector_ids = data.get("canonical_sector_ids") or []
        file_summary["canonical_sector_ids"] = list(canonical_sector_ids)
        if not canonical_sector_ids:
            findings.append(Finding("ERROR", "CANONICAL_SECTOR_IDS_MISSING", "canonical_sector_ids is empty.", rel_path))
        for sid in canonical_sector_ids:
            if sid in valid_sector_ids:
                canonical_sector_binding_count += 1
                continue
            resolved, is_legacy = resolve_sector_id(str(sid), valid_sector_ids, legacy_map)
            if is_legacy and resolved in valid_sector_ids:
                findings.append(
                    Finding(
                        "ERROR",
                        "CANONICAL_SECTOR_ID_IS_LEGACY",
                        f"canonical_sector_ids contains legacy id '{sid}', resolved to '{resolved}'.",
                        rel_path,
                    )
                )
            else:
                findings.append(Finding("ERROR", "CANONICAL_SECTOR_ID_INVALID", f"invalid canonical_sector_id '{sid}'.", rel_path))

        legacy_fields = sorted(LEGACY_TOP_LEVEL.intersection(data))
        file_summary["legacy_only_fields"] = legacy_fields
        legacy_only_field_count += len(legacy_fields)
        if legacy_fields:
            findings.append(
                Finding(
                    "INFO",
                    "LEGACY_FIELDS_RETAINED",
                    f"legacy top-level fields retained for compatibility: {', '.join(legacy_fields)}",
                    rel_path,
                )
            )

        status = str(data.get("status", ""))
        if status.lower() in {"completed", "verified", "research-grade", "research_grade"}:
            findings.append(
                Finding(
                    "WARNING",
                    "EVIDENCE_STATUS_OVERSTATED",
                    f"status='{status}' may overstate migrated evidence readiness.",
                    rel_path,
                )
            )

        source_index = data.get("source_index") or []
        evidence_items = data.get("evidence_items") or []
        file_summary["source_count"] = len(source_index)
        file_summary["evidence_item_count"] = len(evidence_items)
        total_sources += len(source_index)
        total_items += len(evidence_items)

        source_ids: set[str] = set()
        for source in source_index:
            sid = str(source.get("source_id", "") or "")
            if not sid:
                findings.append(Finding("ERROR", "SOURCE_ID_MISSING", "source_index entry missing source_id.", rel_path))
                continue
            if sid in source_ids:
                findings.append(Finding("ERROR", "SOURCE_ID_DUPLICATE", f"duplicate source_id '{sid}'.", rel_path))
            source_ids.add(sid)
            if _is_empty_source_metadata(source):
                missing_source_metadata_count += 1
                file_summary["missing_source_metadata_count"] += 1
                findings.append(
                    Finding(
                        "WARNING",
                        "MISSING_SOURCE_METADATA",
                        f"source_id '{sid}' lacks title/date or url/path metadata.",
                        rel_path,
                    )
                )

        evidence_ids: set[str] = set()
        for item in evidence_items:
            evidence_id = str(item.get("evidence_id", "") or "")
            if not evidence_id:
                findings.append(Finding("ERROR", "EVIDENCE_ID_MISSING", "evidence_items entry missing evidence_id.", rel_path))
            elif evidence_id in evidence_ids:
                findings.append(Finding("ERROR", "EVIDENCE_ID_DUPLICATE", f"duplicate evidence_id '{evidence_id}'.", rel_path))
            evidence_ids.add(evidence_id)

            item_source_id = str(item.get("source_id", "") or "")
            claim = str(item.get("claim", "") or "")
            if claim and not item_source_id:
                findings.append(Finding("ERROR", "CLAIM_WITHOUT_SOURCE_ID", f"claim in evidence_id '{evidence_id}' has no source_id.", rel_path))
            if item_source_id and item_source_id not in source_ids:
                findings.append(
                    Finding(
                        "ERROR",
                        "EVIDENCE_ITEM_SOURCE_ID_UNRESOLVED",
                        f"evidence_id '{evidence_id}' references unknown source_id '{item_source_id}'.",
                        rel_path,
                    )
                )

            item_sector = str(item.get("sector_id", "") or "")
            if item_sector not in valid_sector_ids:
                resolved, is_legacy = resolve_sector_id(item_sector, valid_sector_ids, legacy_map)
                if is_legacy and resolved in valid_sector_ids:
                    findings.append(
                        Finding(
                            "ERROR",
                            "EVIDENCE_ITEM_SECTOR_ID_LEGACY",
                            f"evidence_id '{evidence_id}' uses legacy sector_id '{item_sector}', resolved to '{resolved}'.",
                            rel_path,
                        )
                    )
                else:
                    findings.append(
                        Finding(
                            "ERROR",
                            "EVIDENCE_ITEM_SECTOR_ID_INVALID",
                            f"evidence_id '{evidence_id}' has invalid sector_id '{item_sector}'.",
                            rel_path,
                        )
                    )

        file_summaries.append(file_summary)

    summary = {
        "project_id": project_id,
        "evidence_file_count": len(records),
        "source_count": total_sources,
        "evidence_item_count": total_items,
        "missing_source_metadata_count": missing_source_metadata_count,
        "legacy_only_field_count": legacy_only_field_count,
        "canonical_sector_binding_count": canonical_sector_binding_count,
        "file_summaries": file_summaries,
    }

    if write_report:
        _write_markdown_report(project_id, findings, summary)
    return findings, summary


def _counts(findings: list[Finding]) -> dict[str, int]:
    return {
        "ERROR": sum(1 for f in findings if f.severity == "ERROR"),
        "WARNING": sum(1 for f in findings if f.severity == "WARNING"),
        "INFO": sum(1 for f in findings if f.severity == "INFO"),
    }


def _write_markdown_report(project_id: str, findings: list[Finding], summary: dict[str, Any]) -> None:
    counts = _counts(findings)
    audit_dir = WORKSPACE_ROOT / "investment_system" / "research" / "projects" / project_id / "audits"
    audit_dir.mkdir(parents=True, exist_ok=True)
    path = audit_dir / "evidence_schema_audit.md"
    lines = [
        "# Evidence Schema Audit - Phase 1E-d-b",
        "",
        f"Project: `{project_id}`",
        "",
        "Scope: engineering schema/source_id audit only. This report is not an investment report.",
        "",
        "## Summary",
        "",
        f"- ERROR: {counts['ERROR']}",
        f"- WARNING: {counts['WARNING']}",
        f"- INFO: {counts['INFO']}",
        f"- evidence_file_count: {summary['evidence_file_count']}",
        f"- source_count: {summary['source_count']}",
        f"- evidence_item_count: {summary['evidence_item_count']}",
        f"- missing_source_metadata_count: {summary['missing_source_metadata_count']}",
        f"- legacy_only_field_count: {summary['legacy_only_field_count']}",
        f"- canonical_sector_binding_count: {summary['canonical_sector_binding_count']}",
        "",
        "## Evidence Files",
        "",
        "| evidence_file_id | canonical_sector_ids | sources | evidence_items | missing_source_metadata | legacy_fields |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in summary["file_summaries"]:
        lines.append(
            "| {evidence_file_id} | {sectors} | {source_count} | {evidence_item_count} | {missing} | {legacy} |".format(
                evidence_file_id=row["evidence_file_id"],
                sectors=", ".join(row["canonical_sector_ids"]) or "-",
                source_count=row["source_count"],
                evidence_item_count=row["evidence_item_count"],
                missing=row["missing_source_metadata_count"],
                legacy=", ".join(row["legacy_only_fields"]) or "-",
            )
        )
    lines.extend(["", "## Findings", ""])
    if not findings:
        lines.append("No findings.")
    else:
        for severity in ["ERROR", "WARNING", "INFO"]:
            rows = [f for f in findings if f.severity == severity]
            if not rows:
                continue
            lines.append(f"### {severity}")
            lines.append("")
            for f in rows:
                location = f" (`{f.file}`)" if f.file else ""
                lines.append(f"- `{f.code}`{location}: {f.message}")
            lines.append("")
    lines.extend([
        "## Recommendation",
        "",
        "Evidence schema/source_id normalization has a usable canonical wrapper when ERROR=0. "
        "Warnings about missing source metadata should be resolved before treating migrated legacy evidence as research-grade.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def _print_report(findings: list[Finding], summary: dict[str, Any]) -> None:
    counts = _counts(findings)
    print("Evidence Schema Audit")
    print("=" * 60)
    print(f"project_id                     : {summary['project_id']}")
    print(f"ERROR                          : {counts['ERROR']}")
    print(f"WARNING                        : {counts['WARNING']}")
    print(f"INFO                           : {counts['INFO']}")
    print(f"evidence_file_count            : {summary['evidence_file_count']}")
    print(f"source_count                   : {summary['source_count']}")
    print(f"evidence_item_count            : {summary['evidence_item_count']}")
    print(f"missing_source_metadata_count  : {summary['missing_source_metadata_count']}")
    print(f"legacy_only_field_count        : {summary['legacy_only_field_count']}")
    print(f"canonical_sector_binding_count : {summary['canonical_sector_binding_count']}")
    print()
    print("Evidence files")
    for row in summary["file_summaries"]:
        print(
            f"  - {row['evidence_file_id']}: sources={row['source_count']}, "
            f"items={row['evidence_item_count']}, "
            f"missing_source_metadata={row['missing_source_metadata_count']}, "
            f"sectors={row['canonical_sector_ids']}"
        )
    print()
    for severity in ["ERROR", "WARNING", "INFO"]:
        rows = [f for f in findings if f.severity == severity]
        if not rows:
            continue
        print(f"{severity}s")
        for f in rows:
            location = f" ({f.file})" if f.file else ""
            print(f"  [{f.code}]{location} {f.message}")
        print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit canonical evidence YAML schema/source_id readiness.")
    parser.add_argument("--project", required=True, help="Project ID under research/projects/")
    args = parser.parse_args(argv)
    findings, summary = audit_project(args.project, write_report=True)
    _print_report(findings, summary)
    return 1 if any(f.severity == "ERROR" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
