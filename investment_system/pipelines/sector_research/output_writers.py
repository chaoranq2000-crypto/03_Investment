"""Canonical output writer adapters for project-aware outputs.

Preview writers stay under audits/generator_previews. Formal writers are gated:
callers must explicitly opt in and placeholder score rows cannot carry preview
ratings or generated investment actions.
"""

from __future__ import annotations

import csv
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
    resolve_evidence_files_for_sector,
    validate_output_record_shape,
)


PREVIEW_MARKER = "PREVIEW_ONLY_DO_NOT_USE_FOR_RESEARCH"
PREVIEW_RATING = "PREVIEW_NOT_FOR_INVESTMENT"
FORMAL_SCORING_DISABLED = "FORMAL_SCORING_DISABLED"
NOT_RATED = "NOT_RATED"
GENERATOR_PREVIEW_FILENAMES = {
    "company_table": "preview_company_table.csv",
    "sector_comparison_table": "preview_sector_comparison_table.csv",
    "source_index": "preview_source_index.csv",
    "missing_data_log": "preview_missing_data_log.csv",
    "conflict_data_log": "preview_conflict_data_log.csv",
    "score_table": "preview_score_table.csv",
    "sector_card": "preview_sector_card.md",
}
CSV_OUTPUT_TYPES = [
    "company_table",
    "sector_comparison_table",
    "source_index",
    "missing_data_log",
    "conflict_data_log",
    "score_table",
]


def get_generator_preview_dir(config: ProjectConfig) -> Path:
    return WORKSPACE_ROOT / "investment_system" / "research" / "projects" / config.project_id / "audits" / "generator_previews"


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


def _write_csv_rows(path: Path, fields: list[str], rows: list[dict[str, Any]], mode: str = "w") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()
    with path.open(mode, newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if mode == "w" or not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def _assert_formal_output_path(config: ProjectConfig, path: Path) -> None:
    resolved = path.resolve()
    output_root = config.output_root.resolve()
    preview_dir = get_generator_preview_dir(config).resolve()
    if not str(resolved).startswith(str(output_root)):
        raise RuntimeError(f"formal output path is outside project output root: {resolved}")
    if str(resolved).startswith(str(preview_dir)):
        raise RuntimeError(f"formal output path points to generator preview dir: {resolved}")


def _reject_preview_markers(output_type: str, record: dict[str, Any]) -> None:
    text = "\n".join(str(value) for value in record.values())
    if PREVIEW_MARKER in text or PREVIEW_RATING in text:
        raise RuntimeError(f"{output_type} formal record contains preview marker/rating")
    if str(record.get("data_status", "")).lower() == "preview":
        raise RuntimeError(f"{output_type} formal record has preview data_status")


def _validate_formal_record(config: ProjectConfig, output_type: str, record: dict[str, Any]) -> None:
    _reject_preview_markers(output_type, record)
    result = validate_output_record_shape(config, output_type, record)
    if result.get("errors"):
        raise RuntimeError(f"{output_type} formal record shape failed: {'; '.join(result['errors'])}")


def build_score_placeholder_record(
    config: ProjectConfig,
    sector_id: str,
    *,
    source_ids: str = "",
    evidence_ids: str = "",
    generated_at: str | None = None,
    reason: str = "formal production scoring is disabled; no investment rating generated",
) -> dict[str, Any]:
    """Build a no-data-safe formal score placeholder.

    This is the only formal score_table record allowed before a production
    scoring calculator is explicitly enabled.
    """
    sector = get_sector(config, sector_id)
    generated_at = generated_at or _now_iso()
    reason_text = f"{FORMAL_SCORING_DISABLED}: {reason}"
    record = {
        "project_id": config.project_id,
        "sector_id": sector.get("sector_id", sector_id),
        "sector_name": sector.get("sector_name", sector_id),
        "prosperity_score": "not_applicable",
        "prosperity_reason": reason_text,
        "earnings_certainty_score": "not_applicable",
        "earnings_certainty_reason": reason_text,
        "valuation_score": "not_applicable",
        "valuation_reason": reason_text,
        "trading_comfort_score": "not_applicable",
        "trading_comfort_reason": reason_text,
        "catalyst_score": "not_applicable",
        "catalyst_reason": reason_text,
        "purity_score": "not_applicable",
        "purity_reason": reason_text,
        "risk_control_score": "not_applicable",
        "risk_control_reason": reason_text,
        "total_score": "not_applicable",
        "rating": NOT_RATED,
        "rating_reason": "no formal investment rating generated",
        "source_ids": source_ids or "missing",
        "evidence_ids": evidence_ids or "missing",
        "data_status": "score_placeholder",
        "notes": FORMAL_SCORING_DISABLED,
        "score_version": "score_placeholder_v1",
        "generated_at": generated_at,
    }
    _validate_formal_record(config, "score_table", record)
    return record


def write_score_placeholder(
    config: ProjectConfig,
    sector_id: str,
    path: Path,
    *,
    source_ids: str = "",
    evidence_ids: str = "",
    allow_formal_output: bool = False,
) -> Path:
    """Write a gated formal score_table placeholder to a project output path."""
    if not allow_formal_output:
        raise RuntimeError("formal score placeholder write requires allow_formal_output=True")
    _assert_formal_output_path(config, path)
    record = build_score_placeholder_record(
        config,
        sector_id,
        source_ids=source_ids,
        evidence_ids=evidence_ids,
    )
    _write_csv_rows(path, _field_order(config, "score_table"), [record], mode="w")
    return path


def _markdown_table(fields: list[str], rows: list[dict[str, Any]]) -> str:
    lines = [
        "| " + " | ".join(fields) + " |",
        "| " + " | ".join("---" for _ in fields) + " |",
    ]
    for row in rows:
        values = [str(row.get(field, "")).replace("\n", " ") for field in fields]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def write_canonical_log_records(
    config: ProjectConfig,
    output_type: str,
    rows: list[dict[str, Any]],
    path: Path,
    *,
    allow_formal_output: bool = False,
) -> Path:
    """Write canonical missing/conflict log records to the configured log path."""
    if output_type not in {"missing_data_log", "conflict_data_log"}:
        raise ValueError(f"unsupported canonical log output_type: {output_type}")
    if not allow_formal_output:
        raise RuntimeError(f"{output_type} write requires allow_formal_output=True")
    _assert_formal_output_path(config, path)
    fields = _field_order(config, output_type)
    normalized_rows = rows or []
    for row in normalized_rows:
        _validate_formal_record(config, output_type, row)

    title = "Missing Data Log" if output_type == "missing_data_log" else "Conflict Data Log"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".csv":
        _write_csv_rows(path, fields, normalized_rows, mode="w")
    else:
        body = f"# {title}\n\n"
        body += _markdown_table(fields, normalized_rows) if normalized_rows else _markdown_table(fields, [])
        path.write_text(body, encoding="utf-8")
    return path


def _path_from_evidence_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return WORKSPACE_ROOT / path


def _first_evidence_refs(config: ProjectConfig, sector_id: str) -> dict[str, Any]:
    refs = {
        "source_id": "PREVIEW-MISSING-SOURCE",
        "evidence_id": "PREVIEW-MISSING-EVIDENCE",
        "source": {},
        "evidence_item": {},
        "source_metadata_missing": True,
    }
    evidence_files = resolve_evidence_files_for_sector(config, sector_id)
    for evidence_file in evidence_files:
        path = _path_from_evidence_path(str(evidence_file.get("path", "")))
        if not path.exists():
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        sources = data.get("source_index", []) or []
        items = data.get("evidence_items", []) or []
        source = sources[0] if sources and isinstance(sources[0], dict) else {}
        item = items[0] if items and isinstance(items[0], dict) else {}
        if source.get("source_id"):
            refs["source_id"] = source["source_id"]
            refs["source"] = source
            refs["source_metadata_missing"] = not any(source.get(k) for k in ("title", "url", "path"))
        if item.get("evidence_id"):
            refs["evidence_id"] = item["evidence_id"]
            refs["evidence_item"] = item
        return refs
    return refs


def _stock(config: ProjectConfig, sector_id: str) -> dict[str, Any]:
    stocks = get_stocks_for_sector(config, sector_id, include_pending=False)
    if not stocks:
        raise RuntimeError(f"No listed stocks available for preview sector {sector_id}.")
    return stocks[0]


def _market_from_code(code: str) -> str:
    if "." in code:
        return code.split(".")[-1]
    if code.startswith("6"):
        return "SH"
    if code.startswith(("0", "3")):
        return "SZ"
    if code.startswith(("4", "8")):
        return "BJ"
    return ""


def build_generator_preview_records(config: ProjectConfig, sector_id: str) -> dict[str, dict[str, Any]]:
    """Build minimal project-aware preview records from real sector/stock bindings."""
    sector = get_sector(config, sector_id)
    stock = _stock(config, sector.get("sector_id", sector_id))
    refs = _first_evidence_refs(config, sector.get("sector_id", sector_id))
    source_id = refs["source_id"]
    evidence_id = refs["evidence_id"]
    source = refs["source"]
    generated_at = _now_iso()
    stock_code = stock.get("code", "")
    stock_name = stock.get("name", stock_code)

    common = {
        "project_id": config.project_id,
        "sector_id": sector.get("sector_id", sector_id),
        "sector_name": sector.get("sector_name", sector_id),
        "research_group_id": sector.get("research_group_id", ""),
        "source_ids": source_id,
        "evidence_ids": evidence_id,
        "data_status": "preview",
        "notes": PREVIEW_MARKER,
    }

    return {
        "sector_card": {
            **common,
            "priority": sector.get("priority", ""),
            "status": "preview",
            "generated_at": generated_at,
            "missing_fields": "formal_research_data_not_collected",
            "conflict_flags": "none_in_preview",
        },
        "company_table": {
            **common,
            "stock_code": stock_code,
            "stock_name": stock_name,
            "market": _market_from_code(stock_code),
            "role": stock.get("role", ""),
            "exposure_type": stock.get("exposure_type", ""),
            "coverage_status": "preview_stock_universe_bound",
            "financial_period": "preview_no_financial_fetch",
            "revenue": "missing",
            "net_profit": "missing",
            "gross_margin": "missing",
            "pe_ttm": "missing",
            "pe_2026e": "missing",
            "pe_2027e": "missing",
            "peg": "missing",
            "missing_fields": "financials,valuation,forecast",
            "conflict_flags": "none_in_preview",
        },
        "sector_comparison_table": {
            **common,
            "parent_chain": sector.get("parent_chain") or "preview_parent_chain_not_classified",
            "chain_position": sector.get("chain_position") or "preview_chain_position_not_classified",
            "core_logic": PREVIEW_MARKER,
            "leader_stocks": stock_name,
            "elastic_stocks": stock_name,
            "prosperity_score": "0",
            "prosperity_reason": PREVIEW_MARKER,
            "earnings_certainty_score": "0",
            "earnings_certainty_reason": PREVIEW_MARKER,
            "valuation_score": "0",
            "valuation_reason": PREVIEW_MARKER,
            "trading_comfort_score": "0",
            "trading_comfort_reason": PREVIEW_MARKER,
            "catalyst_score": "0",
            "catalyst_reason": PREVIEW_MARKER,
            "purity_score": "0",
            "purity_reason": PREVIEW_MARKER,
            "risk_control_score": "0",
            "risk_control_reason": PREVIEW_MARKER,
            "total_score": "0",
            "action_rating": PREVIEW_RATING,
            "rating_reason": PREVIEW_MARKER,
            "suggested_action": "preview_only_no_investment_action",
            "missing_data_flags": "formal_research_data_not_collected",
            "key_evidence": PREVIEW_MARKER,
            "key_risk": PREVIEW_MARKER,
            "confidence_level": "preview",
            "generated_at": generated_at,
        },
        "source_index": {
            "project_id": config.project_id,
            "source_id": source_id,
            "subject_type": "sector",
            "subject_id": sector.get("sector_id", sector_id),
            "subject_name": sector.get("sector_name", sector_id),
            "sector_id": sector.get("sector_id", sector_id),
            "claim_supported": PREVIEW_MARKER,
            "source_type": source.get("source_type", "preview_missing_source_metadata"),
            "source_title": source.get("title", "PREVIEW_MISSING_SOURCE_METADATA"),
            "source_date": str(source.get("date", "missing")),
            "url_or_path": source.get("url") or source.get("path") or "PREVIEW_MISSING_SOURCE_METADATA",
            "confidence": source.get("reliability", "preview"),
            "evidence_ids": evidence_id,
            "extracted_fields": "preview_contract_shape",
            "notes": PREVIEW_MARKER,
            "access_status": "preview",
            "retrieved_date": generated_at[:10],
        },
        "missing_data_log": {
            "project_id": config.project_id,
            "output_type": "company_table",
            "sector_id": sector.get("sector_id", sector_id),
            "stock_code": stock_code,
            "stock_name": stock_name,
            "missing_field": "financials",
            "severity": "preview",
            "reason": "formal_data_not_collected_in_dry_run_generate",
            "source_ids": source_id,
            "evidence_ids": evidence_id,
            "notes": PREVIEW_MARKER,
            "current_value": "missing",
            "suggested_acquisition_path": "production_gate_collect_or_cache",
            "source_id": source_id,
            "evidence_id": evidence_id,
            "status": "preview",
        },
        "conflict_data_log": {
            "project_id": config.project_id,
            "output_type": "company_table",
            "sector_id": sector.get("sector_id", sector_id),
            "stock_code": stock_code,
            "stock_name": stock_name,
            "field": "preview_conflict_field",
            "conflicting_values": "none_in_preview",
            "source_ids": source_id,
            "severity": "preview",
            "resolution_status": "preview_no_conflict",
            "resolution_note": PREVIEW_MARKER,
            "handling": "preview_only",
            "evidence_ids": evidence_id,
            "notes": PREVIEW_MARKER,
        },
        "score_table": {
            **common,
            "sector_name": sector.get("sector_name", sector_id),
            "prosperity_score": "0",
            "prosperity_reason": PREVIEW_MARKER,
            "earnings_certainty_score": "0",
            "earnings_certainty_reason": PREVIEW_MARKER,
            "valuation_score": "0",
            "valuation_reason": PREVIEW_MARKER,
            "trading_comfort_score": "0",
            "trading_comfort_reason": PREVIEW_MARKER,
            "catalyst_score": "0",
            "catalyst_reason": PREVIEW_MARKER,
            "purity_score": "0",
            "purity_reason": PREVIEW_MARKER,
            "risk_control_score": "0",
            "risk_control_reason": PREVIEW_MARKER,
            "total_score": "0",
            "rating": PREVIEW_RATING,
            "rating_reason": PREVIEW_MARKER,
            "score_version": "preview_v1",
            "generated_at": generated_at,
        },
    }


def render_sector_card_preview(record: dict[str, Any]) -> str:
    front_matter = {
        "project_id": record.get("project_id"),
        "sector_id": record.get("sector_id"),
        "sector_name": record.get("sector_name"),
        "research_group_id": record.get("research_group_id"),
        "priority": record.get("priority"),
        "status": record.get("status"),
        "generated_at": record.get("generated_at"),
        "source_ids": record.get("source_ids"),
        "evidence_ids": record.get("evidence_ids"),
        "preview_only": True,
        "notes": PREVIEW_MARKER,
    }
    body = [
        PREVIEW_MARKER,
        "",
        "This is a generator preview for field-shape validation only.",
        "No formal investment conclusion, rating, score, or research card was generated.",
    ]
    return "---\n" + yaml.safe_dump(front_matter, allow_unicode=True, sort_keys=False) + "---\n\n" + "\n".join(body) + "\n"


def validate_preview_records(config: ProjectConfig, records: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        output_type: validate_output_record_shape(config, output_type, records.get(output_type, {}))
        for output_type in list_output_types(config)
    }


def _assert_preview_path(config: ProjectConfig, path: Path) -> None:
    resolved = path.resolve()
    preview_dir = get_generator_preview_dir(config).resolve()
    output_root = config.output_root.resolve()
    if not str(resolved).startswith(str(preview_dir)):
        raise RuntimeError(f"preview output path is outside generator preview dir: {resolved}")
    if str(resolved).startswith(str(output_root)):
        raise RuntimeError(f"preview output path would write into formal output root: {resolved}")


def write_generator_preview_files(config: ProjectConfig, records: dict[str, dict[str, Any]]) -> list[Path]:
    preview_dir = get_generator_preview_dir(config)
    preview_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for output_type in CSV_OUTPUT_TYPES:
        path = preview_dir / GENERATOR_PREVIEW_FILENAMES[output_type]
        _assert_preview_path(config, path)
        fields = _field_order(config, output_type)
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerow(records[output_type])
        written.append(path)

    card_path = preview_dir / GENERATOR_PREVIEW_FILENAMES["sector_card"]
    _assert_preview_path(config, card_path)
    card_path.write_text(render_sector_card_preview(records["sector_card"]), encoding="utf-8")
    written.append(card_path)
    return written
