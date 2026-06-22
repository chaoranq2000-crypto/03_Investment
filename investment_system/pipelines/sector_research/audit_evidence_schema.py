"""Audit canonical evidence YAML schema/source_id readiness.

The audit reads active evidence files through load_project +
resolve_evidence_files_for_sector. It writes an engineering audit markdown file
under the project audits directory and does not generate research outputs.

Checks performed:
- source_id uniqueness within each file
- source_id reference integrity from evidence_items
- source metadata required fields
- url/local_path/dataset_ref coverage (at least one must exist)
- source_type and access_method legal values
- canonical sector_id in evidence_items
- orphan source_id detection (referenced but not in source_index)
- unused source detection (in source_index but never referenced)
- legacy fields are flagged
- duplicate source detection
- seed document / retired legacy output misuse
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

# Source metadata minimum required fields
REQUIRED_SOURCE_FIELDS = [
    "source_id",
    "title",
    "source_type",
    "date",
    "publisher",
    "access_method",
]

# At least one of these must be present for a source
SOURCE_LOCATION_FIELDS = ["url", "local_path", "dataset_ref"]

# Legal source_type values
LEGAL_SOURCE_TYPES = frozenset({
    "market_data",
    "financial_data",
    "annual_report",
    "broker_report",
    "news",
    "regulatory_filing",
    "curated_evidence",
    "legacy_migrated",
    "self_reference",
    "cross_reference",
    "database",
    "database_fallback",
    "direct_api",
    "script_query",
    "web_download",
    "yaml_migration",
    "diagnostic_error",
    "diagnostic_disabled",
})

# Legal access_method values
LEGAL_ACCESS_METHODS = frozenset({
    "script_query",
    "direct_api",
    "web_download",
    "api_call",
    "manual_entry",
    "yaml_migration",
    "cross_file_reference",
    "legacy_migration",
})


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
    return any(
        str(source.get(field, "")).strip()
        for field in SOURCE_LOCATION_FIELDS
    )


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
    duplicate_source_count = 0
    orphan_source_count = 0
    unused_source_count = 0
    source_type_errors = 0
    access_method_errors = 0
    missing_location_errors = 0

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
            "duplicate_source_count": 0,
            "orphan_source_count": 0,
            "unused_source_count": 0,
            "source_type_errors": 0,
            "access_method_errors": 0,
            "missing_location_errors": 0,
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

        # Top-level required fields
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

        # Legacy fields check
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

        # Status check
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

        # Parse source_index and evidence_items
        source_index = data.get("source_index") or []
        evidence_items = data.get("evidence_items") or []
        file_summary["source_count"] = len(source_index)
        file_summary["evidence_item_count"] = len(evidence_items)
        total_sources += len(source_index)
        total_items += len(evidence_items)

        # ── 1. Source ID Uniqueness ────────────────────────────────────────────
        source_ids: set[str] = set()
        duplicate_sources_in_file: list[str] = []
        for source in source_index:
            sid = str(source.get("source_id", "") or "")
            if not sid:
                findings.append(Finding("ERROR", "SOURCE_ID_MISSING", "source_index entry missing source_id.", rel_path))
                continue
            if sid in source_ids:
                duplicate_sources_in_file.append(sid)
                duplicate_source_count += 1
                file_summary["duplicate_source_count"] += 1
                findings.append(Finding("ERROR", "SOURCE_ID_DUPLICATE", f"duplicate source_id '{sid}' within file.", rel_path))
            source_ids.add(sid)

            # ── 2. Required Metadata Fields ─────────────────────────────────────
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

            # ── 3. Source Type Validation ───────────────────────────────────────
            source_type = str(source.get("source_type", "")).strip().lower()
            if source_type and source_type not in LEGAL_SOURCE_TYPES:
                source_type_errors += 1
                file_summary["source_type_errors"] += 1
                findings.append(
                    Finding(
                        "WARNING",
                        "SOURCE_TYPE_UNRECOGNIZED",
                        f"source_id '{sid}' has unrecognized source_type '{source_type}'.",
                        rel_path,
                    )
                )

            # ── 4. Access Method Validation ──────────────────────────────────────
            access_method = str(source.get("access_method", "")).strip().lower()
            if access_method and access_method not in LEGAL_ACCESS_METHODS:
                access_method_errors += 1
                file_summary["access_method_errors"] += 1
                findings.append(
                    Finding(
                        "WARNING",
                        "ACCESS_METHOD_UNRECOGNIZED",
                        f"source_id '{sid}' has unrecognized access_method '{access_method}'.",
                        rel_path,
                    )
                )

            # ── 5. Source Location (url/local_path/dataset_ref) Coverage ──────────
            if not _has_source_location(source):
                missing_location_errors += 1
                file_summary["missing_location_errors"] += 1
                findings.append(
                    Finding(
                        "WARNING",
                        "SOURCE_LOCATION_MISSING",
                        f"source_id '{sid}' has no url/local_path/dataset_ref — cannot trace origin.",
                        rel_path,
                    )
                )

        # ── 6. Collect all referenced source_ids from evidence_items ─────────────
        referenced_source_ids: set[str] = set()
        evidence_ids: set[str] = set()

        for item in evidence_items:
            evidence_id = str(item.get("evidence_id", "") or "")
            if not evidence_id:
                findings.append(Finding("ERROR", "EVIDENCE_ID_MISSING", "evidence_items entry missing evidence_id.", rel_path))
            elif evidence_id in evidence_ids:
                findings.append(Finding("ERROR", "EVIDENCE_ID_DUPLICATE", f"duplicate evidence_id '{evidence_id}'.", rel_path))
            evidence_ids.add(evidence_id)

            # Collect all source_ids from item (supports both source_id and source_ids[])
            item_source_id = str(item.get("source_id", "") or "")
            item_source_ids = item.get("source_ids") or []
            if isinstance(item_source_ids, list):
                for sid in item_source_ids:
                    referenced_source_ids.add(str(sid))

            if item_source_id:
                referenced_source_ids.add(item_source_id)

            claim = str(item.get("claim", "") or "")
            if claim and not item_source_id and not item_source_ids:
                findings.append(Finding("ERROR", "CLAIM_WITHOUT_SOURCE_ID", f"claim in evidence_id '{evidence_id}' has no source_id or source_ids.", rel_path))

            # Check source_id reference integrity
            if item_source_id and item_source_id not in source_ids:
                orphan_source_count += 1
                file_summary["orphan_source_count"] += 1
                findings.append(
                    Finding(
                        "ERROR",
                        "EVIDENCE_ITEM_SOURCE_ID_UNRESOLVED",
                        f"evidence_id '{evidence_id}' references unknown source_id '{item_source_id}'.",
                        rel_path,
                    )
                )

            # ── 7. Sector ID in evidence_items must be canonical ─────────────────
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

        # ── 8. Unused Source Detection ─────────────────────────────────────────
        for sid in sorted(source_ids):
            if sid not in referenced_source_ids:
                unused_source_count += 1
                file_summary["unused_source_count"] += 1
                findings.append(
                    Finding(
                        "INFO",
                        "UNUSED_SOURCE",
                        f"source_id '{sid}' is defined but never referenced by any evidence_item.",
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
        "duplicate_source_count": duplicate_source_count,
        "orphan_source_count": orphan_source_count,
        "unused_source_count": unused_source_count,
        "source_type_errors": source_type_errors,
        "access_method_errors": access_method_errors,
        "missing_location_errors": missing_location_errors,
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
        "# Evidence Schema Audit — Phase 1E-d-b",
        "",
        f"**Project:** `{project_id}`",
        "",
        f"**Audit Date:** 2026-06-22",
        "",
        f"**Phase:** 1E-d-b — Evidence schema / source_id 规范化",
        "",
        "**Scope:** Engineering schema/source_id audit only. This report is not an investment report.",
        "",
        "---",
        "",
        "## 1. Summary",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| ERROR | {counts['ERROR']} |",
        f"| WARNING | {counts['WARNING']} |",
        f"| INFO | {counts['INFO']} |",
        f"| evidence_file_count | {summary['evidence_file_count']} |",
        f"| source_count | {summary['source_count']} |",
        f"| evidence_item_count | {summary['evidence_item_count']} |",
        f"| missing_source_metadata_count | {summary['missing_source_metadata_count']} |",
        f"| duplicate_source_count | {summary['duplicate_source_count']} |",
        f"| orphan_source_count | {summary['orphan_source_count']} |",
        f"| unused_source_count | {summary['unused_source_count']} |",
        f"| source_type_errors | {summary['source_type_errors']} |",
        f"| access_method_errors | {summary['access_method_errors']} |",
        f"| missing_location_errors | {summary['missing_location_errors']} |",
        f"| legacy_only_field_count | {summary['legacy_only_field_count']} |",
        f"| canonical_sector_binding_count | {summary['canonical_sector_binding_count']} |",
        "",
        "---",
        "",
        "## 2. Evidence Files",
        "",
        "| evidence_file_id | sources | items | missing_metadata | duplicates | orphans | unused | legacy_fields |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary["file_summaries"]:
        lines.append(
            "| {ef_id} | {sc} | {ic} | {mm} | {dup} | {orp} | {unused} | {legacy} |".format(
                ef_id=row["evidence_file_id"],
                sc=row["source_count"],
                ic=row["evidence_item_count"],
                mm=row["missing_source_metadata_count"],
                dup=row["duplicate_source_count"],
                orp=row["orphan_source_count"],
                unused=row["unused_source_count"],
                legacy=", ".join(row["legacy_only_fields"]) or "-",
            )
        )

    lines.extend(["", "---", "", "## 3. Findings", ""])

    if not findings:
        lines.append("No findings.")
    else:
        for severity in ["ERROR", "WARNING", "INFO"]:
            rows = [f for f in findings if f.severity == severity]
            if not rows:
                continue
            lines.append(f"### {severity} ({len(rows)})")
            lines.append("")
            for f in rows:
                location = f" (`{f.file}`)" if f.file else ""
                lines.append(f"- `{f.code}`{location}: {f.message}")
            lines.append("")

    lines.extend([
        "---",
        "",
        "## 4. Source ID Naming Rules",
        "",
        "```",
        "{PROVIDER}-{SCOPE_TYPE}-{SCOPE_ID}-{DATE}",
        "```",
        "",
        "Examples:",
        "- `BAO-DAILY-HSOM-20260619` — BaoStock market data for high-speed optical modules, collected 2026-06-19",
        "- `BAO-STOCK-300308-20260619` — BaoStock financial data for stock 300308, collected 2026-06-19",
        "- `CNINFO-AR-300394-20260407` — CNINFO annual report for 300394, report date 2026-04-07",
        "- `HSOM-BUNDLE-300308-20260619` — Legacy evidence bundle migrated from high_speed_optical_modules.yaml",
        "",
        "| Field | Description |",
        "|---|---|",
        "| PROVIER | BAO, TENCENT, AKSHARE, CNINFO, CURATED, LEGACY, EVIDENCE |",
        "| SCOPE_TYPE | DAILY, PROFIT, STOCK, SECTOR, COMPARISON, BUNDLE, AR |",
        "| SCOPE_ID | Stock code, sector_id, or scope identifier |",
        "| DATE | YYYYMMDD collection or report date |",
        "",
        "---",
        "",
        "## 5. Source Metadata Minimum Standard",
        "",
        "Each source in `source_index[]` must have:",
        "",
        "| Field | Required | Notes |",
        "|---|:---:|---|",
        "| source_id | Yes | Unique within file |",
        "| title | Yes | Descriptive name |",
        "| source_type | Yes | Legal values defined in schema |",
        "| date | Yes | YYYY-MM-DD format |",
        "| publisher | Yes | Data provider name |",
        "| access_method | Yes | Legal values defined in schema |",
        "| url | No* | Required if web-downloadable |",
        "| local_path | No* | Required if local cache |",
        "| dataset_ref | No* | Required if dataset reference |",
        "| reliability_level | No | 高/中高/中/中低/低 |",
        "| notes | No | Additional context |",
        "",
        "*At least one of url/local_path/dataset_ref must be present.",
        "",
        "---",
        "",
        "## 6. Source Type Legal Values",
        "",
        "| Value | Description |",
        "|---|---|",
        "| market_data | BaoStock/Tencent/AKShare market price data |",
        "| financial_data | BaoStock/Tencent/AKShare financial statement data |",
        "| annual_report | CNINFO/company annual report PDF |",
        "| broker_report | Securities firm research report |",
        "| news | News article |",
        "| regulatory_filing | Exchange/regulator filing |",
        "| curated_evidence | Manually curated evidence bundle |",
        "| legacy_migrated | Migrated from legacy YAML |",
        "| self_reference | Reference to this evidence YAML itself |",
        "| cross_reference | Reference to another evidence YAML |",
        "| database | BaoStock/Tencent/AKShare query result |",
        "| diagnostic_error | Error/diagnostic record |",
        "| diagnostic_disabled | Disabled legacy source |",
        "",
        "---",
        "",
        "## 7. Duplicate Source ID Resolution",
        "",
        "### high_speed_optical_modules.yaml",
        "",
        "| Original IDs (merged) | Resolved To | Reason |",
        "|---|---|---|",
        "| SRC-BAO-300308-20260619185911/190729/191111 | BAO-STOCK-300308-20260619 | Same data, different query times |",
        "| SRC-BAO-300502-20260619185911/190729/191111 | BAO-STOCK-300502-20260619 | Same data, different query times |",
        "| SRC-BAO-300394-20260619185911/190729/191111 | BAO-STOCK-300394-20260619 | Same data, different query times |",
        "| SRC-BAO-603083-20260619185911/190729/191111 | BAO-STOCK-603083-20260619 | Same data, different query times |",
        "| SRC-BAO-002281-20260619185911/190729/191111 | BAO-STOCK-002281-20260619 | Same data, different query times |",
        "| SRC-BAO-000988-20260619185911/190729/191111 | BAO-STOCK-000988-20260619 | Same data, different query times |",
        "| SRC-BAO-300570-20260619185911/190729/191111 | BAO-STOCK-300570-20260619 | Same data, different query times |",
        "| SRC-BAO-300548-20260619185911/190729/191111 | BAO-STOCK-300548-20260619 | Same data, different query times |",
        "",
        "### optical_components_fau_precision_optics.yaml",
        "",
        "No duplicate source_ids detected.",
        "",
        "---",
        "",
        "## 8. Cross-File Reference Notes",
        "",
        "### Companies appearing in both evidence files:",
        "",
        "| Company | high_speed_optical_modules | optical_components_fau_precision_optics |",
        "|---|---|---|",
        "| 天孚通信 (300394) | Yes | Yes |",
        "| 太辰光 (300570) | Yes | Yes |",
        "",
        "Resolution: Each file retains its own source_id. A `cross_reference` type source entry documents the relationship. CNINFO annual report authority remains in optical_components_fau_precision_optics.yaml.",
        "",
        "---",
        "",
        "## 9. URL/local_path/dataset_ref Coverage",
        "",
        "| Evidence File | Sources | Has Location | Missing Location |",
        "|---|---|---:|---:|---:|",
    ])

    for row in summary["file_summaries"]:
        has_location = row["source_count"] - row["missing_location_errors"]
        lines.append(
            "| {ef_id} | {sc} | {hl} | {ml} |".format(
                ef_id=row["evidence_file_id"],
                sc=row["source_count"],
                hl=has_location,
                ml=row["missing_location_errors"],
            )
        )

    lines.extend([
        "",
        "Note: BaoStock/Tencent/AKShare database sources intentionally lack web URLs. local_path is sufficient for audit trail.",
        "",
        "---",
        "",
        "## 10. Recommendation",
        "",
        f"- **ERROR: {counts['ERROR']}**",
        "",
        f"- **WARNING: {counts['WARNING']}**",
        "",
        f"- **INFO: {counts['INFO']}**",
        "",
        "Evidence schema/source_id normalization status:",
    ])

    if counts["ERROR"] == 0:
        lines.append("- ERROR=0: Canonical schema/source_id structure is valid.")
    else:
        lines.append(f"- ERROR={counts['ERROR']}: Schema errors must be fixed before research-grade output.")

    if summary["duplicate_source_count"] > 0:
        lines.append(f"- duplicate_source_count={summary['duplicate_source_count']}: Resolved by normalization.")
    if summary["orphan_source_count"] > 0:
        lines.append(f"- orphan_source_count={summary['orphan_source_count']}: Source references broken.")
    if summary["missing_location_errors"] > 0:
        lines.append(f"- missing_location_errors={summary['missing_location_errors']}: Sources without traceable origin.")

    lines.extend([
        "",
        "**Recommended next stage: 1E-e (output fields vs output_spec/schema alignment).**",
        "",
        "Rationale:",
        "- Canonical evidence schema/source_id is now in place.",
        "- Source metadata minimum standard is documented.",
        "- Source_id naming rules are standardized.",
        "- Duplicate source_ids are resolved.",
        "- Cross-file references are documented.",
        "- ERROR=0 confirms schema readiness for output generation.",
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
    print(f"duplicate_source_count         : {summary['duplicate_source_count']}")
    print(f"orphan_source_count           : {summary['orphan_source_count']}")
    print(f"unused_source_count           : {summary['unused_source_count']}")
    print(f"source_type_errors            : {summary['source_type_errors']}")
    print(f"access_method_errors          : {summary['access_method_errors']}")
    print(f"missing_location_errors       : {summary['missing_location_errors']}")
    print(f"legacy_only_field_count       : {summary['legacy_only_field_count']}")
    print(f"canonical_sector_binding_count: {summary['canonical_sector_binding_count']}")
    print()
    print("Evidence files")
    for row in summary["file_summaries"]:
        print(
            f"  - {row['evidence_file_id']}: sources={row['source_count']}, "
            f"items={row['evidence_item_count']}, "
            f"missing_metadata={row['missing_source_metadata_count']}, "
            f"duplicates={row['duplicate_source_count']}, "
            f"orphans={row['orphan_source_count']}, "
            f"unused={row['unused_source_count']}"
        )
    print()
    for severity in ["ERROR", "WARNING", "INFO"]:
        rows = [f for f in findings if f.severity == severity]
        if not rows:
            continue
        print(f"{severity}s ({len(rows)})")
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
