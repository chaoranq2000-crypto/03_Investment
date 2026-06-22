"""Build contract-aligned mock outputs for project-aware output dry-runs.

This module never writes formal research outputs. Optional files are restricted
to the project audit mock directory.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from investment_system.pipelines.sector_research.load_project import (
    WORKSPACE_ROOT,
    ProjectConfig,
    get_output_contract,
    get_sector,
    get_stocks_for_sector,
    list_output_types,
    load_project,
    validate_output_record_shape,
)


MOCK_MARKER = "MOCK_ONLY_DO_NOT_USE_FOR_RESEARCH"
PREFERRED_SECTORS = [
    "cpo_optical_module_silicon_photonics",
    "optical_chip_components",
]
CSV_OUTPUT_TYPES = [
    "company_table",
    "sector_comparison_table",
    "source_index",
    "missing_data_log",
    "conflict_data_log",
    "score_table",
]
MOCK_FILENAMES = {
    "company_table": "mock_company_table.csv",
    "sector_comparison_table": "mock_sector_comparison_table.csv",
    "source_index": "mock_source_index.csv",
    "missing_data_log": "mock_missing_data_log.csv",
    "conflict_data_log": "mock_conflict_data_log.csv",
    "score_table": "mock_score_table.csv",
    "sector_card": "mock_sector_card.md",
}


def get_mock_output_dir(config: ProjectConfig) -> Path:
    return WORKSPACE_ROOT / "investment_system" / "research" / "projects" / config.project_id / "audits" / "mock_outputs"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _field_order(config: ProjectConfig, output_type: str) -> list[str]:
    contract = get_output_contract(config, output_type)
    fields: list[str] = []
    for key in ("required_fields", "optional_fields"):
        for field in contract.get(key, []) or []:
            if field not in fields:
                fields.append(field)
    return fields


def _sector(config: ProjectConfig, sector_id: str | None) -> dict[str, Any]:
    if sector_id:
        try:
            return get_sector(config, sector_id)
        except KeyError:
            raise RuntimeError(f"Sector '{sector_id}' not found in project.")
    for preferred in PREFERRED_SECTORS:
        try:
            return get_sector(config, preferred)
        except KeyError:
            continue
    sectors = config.raw.get("sectors", []) or []
    if not sectors:
        raise RuntimeError("No sectors available for mock output generation.")
    return sectors[0]


def _stock(config: ProjectConfig, sector_id: str) -> dict[str, Any]:
    stocks = get_stocks_for_sector(config, sector_id)
    if stocks:
        return stocks[0]
    all_stocks = config.raw.get("stocks", []) or []
    if not all_stocks:
        raise RuntimeError("No stocks available for mock output generation.")
    stock = all_stocks[0]
    return {
        "code": stock.get("code", "MOCK.STK"),
        "name": stock.get("name", "MOCK_STOCK"),
        "role": stock.get("role", "mock"),
        "exposure_type": stock.get("exposure_type", "mock"),
        "status": stock.get("status", "mock"),
        "notes": stock.get("notes", ""),
    }


def build_mock_records(config: ProjectConfig, sector_id: str | None = None) -> dict[str, dict[str, Any]]:
    sector = _sector(config, sector_id)
    sector_id_resolved = sector.get("sector_id", PREFERRED_SECTORS[0])
    stock = _stock(config, sector_id_resolved)
    stock_code = stock.get("code", "MOCK.STK")
    stock_name = stock.get("name", "MOCK_STOCK")
    generated_at = _now_iso()

    source_id = "MOCK-SOURCE-001"
    evidence_id = "MOCK-EVIDENCE-001"
    source_ids = source_id
    evidence_ids = evidence_id

    common = {
        "project_id": config.project_id,
        "sector_id": sector_id_resolved,
        "sector_name": sector.get("sector_name", sector_id_resolved),
        "research_group_id": sector.get("research_group_id", ""),
        "source_ids": source_ids,
        "evidence_ids": evidence_ids,
        "notes": MOCK_MARKER,
    }

    return {
        "sector_card": {
            **common,
            "priority": sector.get("priority", "P0"),
            "status": "mock",
            "generated_at": generated_at,
            "missing_fields": "mock_missing_field",
            "conflict_flags": "none",
        },
        "company_table": {
            **common,
            "stock_code": stock_code,
            "stock_name": stock_name,
            "market": "A股",
            "role": stock.get("role", "mock"),
            "exposure_type": stock.get("exposure_type", "mock"),
            "coverage_status": "mock",
            "data_status": "mock",
            "financial_period": "mock_period",
            "revenue": "mock",
            "net_profit": "mock",
            "gross_margin": "mock",
            "pe_ttm": "mock",
            "pe_2026e": "mock",
            "pe_2027e": "mock",
            "peg": "mock",
            "missing_fields": "mock_missing_field",
            "conflict_flags": "none",
        },
        "sector_comparison_table": {
            **common,
            "parent_chain": sector.get("parent_chain", "mock_parent_chain"),
            "chain_position": sector.get("chain_position", "mock_chain_position"),
            "core_logic": MOCK_MARKER,
            "leader_stocks": stock_name,
            "elastic_stocks": stock_name,
            "prosperity_score": "5",
            "prosperity_reason": MOCK_MARKER,
            "earnings_certainty_score": "5",
            "earnings_certainty_reason": MOCK_MARKER,
            "valuation_score": "5",
            "valuation_reason": MOCK_MARKER,
            "trading_comfort_score": "5",
            "trading_comfort_reason": MOCK_MARKER,
            "catalyst_score": "5",
            "catalyst_reason": MOCK_MARKER,
            "purity_score": "5",
            "purity_reason": MOCK_MARKER,
            "risk_control_score": "5",
            "risk_control_reason": MOCK_MARKER,
            "total_score": "5",
            "action_rating": "MOCK",
            "rating_reason": MOCK_MARKER,
            "suggested_action": MOCK_MARKER,
            "missing_data_flags": "mock_missing_field",
            "key_evidence": MOCK_MARKER,
            "key_risk": MOCK_MARKER,
            "confidence_level": "mock",
            "generated_at": generated_at,
        },
        "source_index": {
            "project_id": config.project_id,
            "source_id": source_id,
            "subject_type": "sector",
            "subject_id": sector_id_resolved,
            "subject_name": sector.get("sector_name", sector_id_resolved),
            "sector_id": sector_id_resolved,
            "claim_supported": MOCK_MARKER,
            "source_type": "other",
            "source_title": MOCK_MARKER,
            "source_date": "mock_date",
            "url_or_path": "audits/mock_outputs/mock_source_index.csv",
            "confidence": "mock",
            "evidence_ids": evidence_ids,
            "extracted_fields": "mock",
            "notes": MOCK_MARKER,
            "access_status": "mock",
            "retrieved_date": "mock_date",
        },
        "missing_data_log": {
            "project_id": config.project_id,
            "output_type": "company_table",
            "sector_id": sector_id_resolved,
            "missing_field": "mock_missing_field",
            "severity": "mock",
            "reason": MOCK_MARKER,
            "source_ids": source_ids,
            "notes": MOCK_MARKER,
            "stock_code": stock_code,
            "stock_name": stock_name,
            "current_value": "mock",
            "suggested_acquisition_path": MOCK_MARKER,
            "source_id": source_id,
            "evidence_id": evidence_id,
            "evidence_ids": evidence_ids,
            "status": "mock",
        },
        "conflict_data_log": {
            "project_id": config.project_id,
            "output_type": "company_table",
            "sector_id": sector_id_resolved,
            "field": "mock_conflict_field",
            "conflicting_values": "mock_a|mock_b",
            "source_ids": source_ids,
            "severity": "mock",
            "resolution_status": "mock",
            "notes": MOCK_MARKER,
            "stock_code": stock_code,
            "stock_name": stock_name,
            "resolution_note": MOCK_MARKER,
            "handling": "mock",
            "evidence_ids": evidence_ids,
        },
        "score_table": {
            "project_id": config.project_id,
            "sector_id": sector_id_resolved,
            "sector_name": sector.get("sector_name", sector_id_resolved),
            "prosperity_score": "5",
            "prosperity_reason": MOCK_MARKER,
            "earnings_certainty_score": "5",
            "earnings_certainty_reason": MOCK_MARKER,
            "valuation_score": "5",
            "valuation_reason": MOCK_MARKER,
            "trading_comfort_score": "5",
            "trading_comfort_reason": MOCK_MARKER,
            "catalyst_score": "5",
            "catalyst_reason": MOCK_MARKER,
            "purity_score": "5",
            "purity_reason": MOCK_MARKER,
            "risk_control_score": "5",
            "risk_control_reason": MOCK_MARKER,
            "total_score": "5",
            "rating": "MOCK_NOT_FOR_INVESTMENT",
            "rating_reason": MOCK_MARKER,
            "source_ids": source_ids,
            "evidence_ids": evidence_ids,
            "data_status": "mock",
            "notes": MOCK_MARKER,
            "score_version": "mock",
            "generated_at": generated_at,
        },
    }


def render_sector_card_front_matter(record: dict[str, Any]) -> str:
    front_matter = {
        "project_id": record.get("project_id"),
        "sector_id": record.get("sector_id"),
        "sector_name": record.get("sector_name"),
        "research_group_id": record.get("research_group_id"),
        "status": record.get("status"),
        "generated_at": record.get("generated_at"),
        "source_ids": record.get("source_ids"),
        "evidence_ids": record.get("evidence_ids"),
        "mock_only": True,
        "notes": MOCK_MARKER,
    }
    return "---\n" + yaml.safe_dump(front_matter, allow_unicode=True, sort_keys=False) + "---\n\n" + MOCK_MARKER + "\n"


def _assert_audit_path(config: ProjectConfig, path: Path) -> None:
    target = path.resolve()
    audit_dir = get_mock_output_dir(config).resolve()
    output_root = config.output_root.resolve()
    if not str(target).startswith(str(audit_dir)):
        raise RuntimeError(f"mock output path is outside audit mock dir: {target}")
    if str(target).startswith(str(output_root)):
        raise RuntimeError(f"mock output path would write into formal output root: {target}")


def write_audit_mock_files(config: ProjectConfig, records: dict[str, dict[str, Any]]) -> list[Path]:
    out_dir = get_mock_output_dir(config)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for output_type in CSV_OUTPUT_TYPES:
        path = out_dir / MOCK_FILENAMES[output_type]
        _assert_audit_path(config, path)
        fields = _field_order(config, output_type)
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerow(records[output_type])
        written.append(path)

    card_path = out_dir / MOCK_FILENAMES["sector_card"]
    _assert_audit_path(config, card_path)
    card_path.write_text(render_sector_card_front_matter(records["sector_card"]), encoding="utf-8")
    written.append(card_path)
    return written


def validate_records(config: ProjectConfig, records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    results = {}
    for output_type in list_output_types(config):
        record = records.get(output_type)
        if not record:
            results[output_type] = {
                "ok": False,
                "errors": [f"{output_type} mock record was not built"],
                "warnings": [],
                "output_type": output_type,
            }
            continue
        results[output_type] = validate_output_record_shape(config, output_type, record)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build project-aware mock output records.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--sector-id", default=None, help="Canonical sector_id for mock output. Defaults to preferred sectors.")
    parser.add_argument("--clean", action="store_true", help="Remove existing mock files before writing.")
    parser.add_argument("--dry-run", action="store_true", help="Print records only; no files written.")
    parser.add_argument("--write-audit-mock-files", action="store_true", help="Write mock files under audits/mock_outputs only.")
    args = parser.parse_args(argv)

    if not args.dry_run and not args.write_audit_mock_files:
        args.dry_run = True

    config = load_project(args.project, create_dirs=False, strict=False, silent=True)
    records = build_mock_records(config, args.sector_id)
    results = validate_records(config, records)

    print(f"Mock output builder project: {config.project_id}")
    print(f"sector_id: {args.sector_id or 'default_preferred'}")
    print(f"output_type_count: {len(list_output_types(config))}")
    print(f"mock_record_count: {len(records)}")
    print(f"record_shape_pass_count: {sum(1 for item in results.values() if item.get('ok'))}")
    print(f"record_shape_fail_count: {sum(1 for item in results.values() if not item.get('ok'))}")

    if args.clean:
        mock_dir = get_mock_output_dir(config)
        if mock_dir.exists():
            import shutil
            for name in MOCK_FILENAMES.values():
                path = mock_dir / name
                if path.exists():
                    path.unlink()
                    print(f"removed: {path}")
        print("clean: done")

    if args.dry_run:
        print("dry_run: true")
        print("No files written.")
        print(json.dumps(records, ensure_ascii=False, indent=2))

    if args.write_audit_mock_files:
        written = write_audit_mock_files(config, records)
        print("write_audit_mock_files: true")
        for path in written:
            print(f"wrote: {path}")

    failures = [item for item in results.values() if not item.get("ok")]
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
