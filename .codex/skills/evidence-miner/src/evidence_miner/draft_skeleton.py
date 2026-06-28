"""Build draft evidence YAML skeletons from official source manifests.

This helper standardizes the handoff from source manifests to evidence
authoring. It writes draft artifacts under the project audit directory only;
it does not register evidence, bind sectors, or write formal research outputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from investment_system.core.project_loader import (
    PROJECTS_ROOT,
    WORKSPACE_ROOT,
    get_sector,
    get_stocks_for_sector,
    load_project,
)


SOURCE_TYPE_MAP = {
    "data_cache": "database",
}

ACCESS_METHOD_MAP = {
    "local_cache": "web_download",
}

RELIABILITY_BY_LEVEL = {
    "strong": "高",
    "supporting": "中高",
    "context": "中",
    "context_only": "中",
}


def _resolve_path(raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else WORKSPACE_ROOT / path


def _workspace_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(WORKSPACE_ROOT).as_posix()
    except ValueError:
        return str(path)


def _slug(text: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "-", text.upper()).strip("-")
    return value or "UNKNOWN"


def _load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"source manifest is not a JSON object: {path}")
    if "records" not in data or not isinstance(data["records"], list):
        raise ValueError(f"source manifest has no records[] list: {path}")
    return data


def _source_type(record: dict[str, Any]) -> str:
    raw = str(record.get("source_type") or "").strip()
    return SOURCE_TYPE_MAP.get(raw, raw or "curated_evidence")


def _access_method(record: dict[str, Any]) -> str:
    raw = str(record.get("access_method") or "").strip()
    return ACCESS_METHOD_MAP.get(raw, raw or "manual_entry")


def _company_lookup(config: Any, sector_id: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for stock in get_stocks_for_sector(config, sector_id, include_pending=False):
        code = str(stock.get("code") or "")
        name = str(stock.get("name") or "")
        if code and name:
            result[code] = name
    return result


def _source_row(record: dict[str, Any]) -> dict[str, Any]:
    evidence_level = str(record.get("evidence_level") or "").strip().lower()
    local_path = str(record.get("text_path") or record.get("local_path") or "")
    row = {
        "source_id": str(record.get("source_id") or ""),
        "source_type": _source_type(record),
        "title": str(record.get("title") or ""),
        "publisher": str(record.get("publisher") or ""),
        "date": str(record.get("source_date") or ""),
        "url": str(record.get("source_url") or ""),
        "access_method": _access_method(record),
        "local_path": local_path,
        "reliability_level": RELIABILITY_BY_LEVEL.get(evidence_level, "待核验"),
        "notes": (
            "Draft source row generated from source manifest. "
            "Manual extraction is required before registration as active evidence. "
            f"file_sha256={record.get('file_sha256') or ''}"
        ),
    }
    return row


def _evidence_type(record: dict[str, Any]) -> str:
    source_type = str(record.get("source_type") or "").strip()
    if source_type == "annual_report":
        return "draft_annual_report_extraction"
    if source_type in {"financial_data", "market_data", "data_cache"}:
        return "draft_data_cache_extraction"
    if source_type in {"investor_relations", "exchange_qa", "announcement"}:
        return f"draft_{source_type}_extraction"
    return "draft_source_extraction"


def _evidence_id(sector_id: str, record: dict[str, Any], run_date: str) -> str:
    source_id = str(record.get("source_id") or "")
    subject = str(record.get("company_code") or source_id or record.get("title") or "source")
    digest = hashlib.sha1(source_id.encode("utf-8")).hexdigest()[:8].upper()
    return f"EV-DRAFT-{_slug(sector_id)}-{_slug(subject)[:24]}-{digest}-{run_date.replace('-', '')}"


def _evidence_item(
    *,
    project_id: str,
    sector_id: str,
    sector_name: str,
    company_names: dict[str, str],
    record: dict[str, Any],
    run_date: str,
) -> dict[str, Any]:
    company_code = str(record.get("company_code") or "")
    company_name = str(record.get("company_name") or company_names.get(company_code, ""))
    subject_type = "company" if company_code else "sector"
    subject_id = company_code or sector_id
    subject_name = company_name or sector_name
    source_file = str(record.get("text_path") or record.get("local_path") or "")
    source_date = str(record.get("source_date") or "")
    return {
        "evidence_id": _evidence_id(sector_id, record, run_date),
        "source_id": str(record.get("source_id") or ""),
        "source_ids": [str(record.get("source_id") or "")],
        "project_id": project_id,
        "sector_id": sector_id,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "subject_name": subject_name,
        "company_code": company_code,
        "company_name": company_name,
        "evidence_level": str(record.get("evidence_level") or "draft"),
        "evidence_type": _evidence_type(record),
        "source_url": str(record.get("source_url") or ""),
        "source_file": source_file,
        "source_date": source_date,
        "extracted_text": (
            "TODO_MANUAL_EXTRACTION: extract a short field-specific excerpt "
            "from the source_file before this draft is promoted to active evidence."
        ),
        "claim": (
            "DRAFT_PLACEHOLDER: source is indexed, but no field-specific claim "
            "has been curated yet. Do not use this item for candidate generation "
            "or formal research output until the claim is replaced with a "
            "source-backed assertion."
        ),
        "metrics_supported": ["draft_placeholder"],
        "time_scope": source_date or "unknown",
        "confidence": "待核验",
        "used_for": ["manual_evidence_curation_only"],
        "not_allowed_for": [
            "sector_card",
            "candidate_generation",
            "investment_conclusion",
            "position_sizing",
            "final_rating",
        ],
        "limitation": (
            "Draft skeleton only. It proves source availability, not product "
            "stage, customer/order status, certification, capacity, revenue split, "
            "or investment conclusion."
        ),
        "missing_fields": [
            "field_specific_excerpt",
            "curated_claim",
            "product_stage",
            "customer_order_certification",
            "capacity_or_project_progress",
            "revenue_or_business_split",
        ],
        "review_status": "needs_manual_extraction",
    }


def build_skeleton(
    *,
    project_id: str,
    sector_id: str,
    manifest_paths: list[Path],
    evidence_file_id: str,
    run_date: str,
) -> dict[str, Any]:
    config = load_project(project_id, create_dirs=False, strict=False, silent=True)
    sector = get_sector(config, sector_id)
    canonical_sector_id = str(sector.get("sector_id") or sector_id)
    sector_name = str(sector.get("sector_name") or canonical_sector_id)
    company_names = _company_lookup(config, canonical_sector_id)

    manifests = [_load_manifest(path) for path in manifest_paths]
    records: list[dict[str, Any]] = []
    for manifest in manifests:
        manifest_sector = str(manifest.get("sector_id") or "")
        if manifest_sector and manifest_sector != canonical_sector_id:
            raise ValueError(
                f"manifest sector_id mismatch: {manifest_sector} != {canonical_sector_id}"
            )
        records.extend(manifest.get("records") or [])

    source_index = [_source_row(record) for record in records]
    evidence_items = [
        _evidence_item(
            project_id=project_id,
            sector_id=canonical_sector_id,
            sector_name=sector_name,
            company_names=company_names,
            record=record,
            run_date=run_date,
        )
        for record in records
    ]

    return {
        "schema_version": "1.1",
        "evidence_file_id": evidence_file_id,
        "status": "draft_source_skeleton",
        "project_ids": [project_id],
        "canonical_sector_ids": [canonical_sector_id],
        "_draft_metadata": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_date": run_date,
            "generated_by": "build_evidence_skeleton.py",
            "source_manifest_paths": [_workspace_relative(path) for path in manifest_paths],
            "record_count": len(records),
            "registration_status": "not_registered",
            "formal_output_status": "not_formal_output",
            "instruction": (
                "Curate extracted_text, claim, metrics_supported, limitation, "
                "and missing_fields before copying this file into "
                "investment_system/research/evidence/ and registering it."
            ),
        },
        "source_index": source_index,
        "evidence_items": evidence_items,
    }


def _default_output_path(project_id: str, sector_id: str, evidence_file_id: str, run_date: str) -> Path:
    return (
        PROJECTS_ROOT
        / project_id
        / "audits"
        / "evidence_drafts"
        / sector_id
        / run_date
        / f"{evidence_file_id}.yaml"
    )


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Build draft evidence YAML skeletons from source manifests.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--sector-id", required=True)
    parser.add_argument("--source-manifest", action="append", default=[])
    parser.add_argument("--evidence-file-id", default="")
    parser.add_argument("--output-path", default="")
    parser.add_argument("--run-date", default=date.today().isoformat())
    parser.add_argument("--write-draft", action="store_true")
    args = parser.parse_args(argv)

    if not args.source_manifest:
        print("ERROR: provide at least one --source-manifest.")
        return 2

    manifest_paths = [_resolve_path(path) for path in args.source_manifest]
    missing = [str(path) for path in manifest_paths if not path.exists()]
    if missing:
        print("ERROR: source manifest not found:")
        for path in missing:
            print(f"  - {path}")
        return 2

    evidence_file_id = args.evidence_file_id or f"draft_{args.sector_id}_{args.run_date.replace('-', '')}"
    output_path = _resolve_path(args.output_path) if args.output_path else _default_output_path(
        args.project,
        args.sector_id,
        evidence_file_id,
        args.run_date,
    )

    try:
        skeleton = build_skeleton(
            project_id=args.project,
            sector_id=args.sector_id,
            manifest_paths=manifest_paths,
            evidence_file_id=evidence_file_id,
            run_date=args.run_date,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    if args.write_draft:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            yaml.safe_dump(skeleton, allow_unicode=True, sort_keys=False, width=100),
            encoding="utf-8",
        )

    print("Draft evidence skeleton")
    print(f"project_id: {args.project}")
    print(f"sector_id: {skeleton['canonical_sector_ids'][0]}")
    print(f"evidence_file_id: {skeleton['evidence_file_id']}")
    print(f"source_count: {len(skeleton['source_index'])}")
    print(f"evidence_item_count: {len(skeleton['evidence_items'])}")
    print(f"write_draft: {args.write_draft}")
    print(f"output_path: {output_path}")
    for item in skeleton["evidence_items"]:
        print(f"- {item['evidence_id']} | {item['source_id']} | {item['review_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
