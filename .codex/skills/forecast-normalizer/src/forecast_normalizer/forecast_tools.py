"""Forecast normalization preview and lightweight source-count audits."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from investment_system.core.constants import WORKSPACE_ROOT


def _resolve_path(raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else WORKSPACE_ROOT / path


def _emit(payload: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


def _load_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and payload.get("schema_version") == "tushare_raw_cache.v1":
        rows = payload.get("rows") or []
        return [row for row in rows if isinstance(row, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return [row for row in payload["records"] if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def _normalize_fields(args: argparse.Namespace) -> int:
    payload = {
        "command": "normalize-forecast-fields",
        "dry_run": True,
        "project": args.project,
        "sector_id": args.sector_id,
        "source_labels": [
            "tushare_report_rc",
            "tushare_research_report_metadata",
            "curated_broker_report",
            "public_web_page",
            "user_provided",
            "unavailable",
        ],
        "normalized_fields": [
            "forecast_period",
            "forecast_source_type",
            "forecast_source_count",
            "report_date",
            "org_name",
            "eps_2026e",
            "eps_2027e",
            "pe_2026e",
            "pe_2027e",
            "peg_2026e",
            "forecast_change_notes",
        ],
        "rules": [
            "Do not call a single broker row consensus.",
            "Keep actual, TTM, 2026E, and 2027E labels separate.",
            "Preserve report_date/org_name/source_id near every forecast field.",
            "Use missing-data logs when no verifiable source row exists.",
        ],
    }
    _emit(payload, args.format)
    return 0


def _audit_source_count(args: argparse.Namespace) -> int:
    path = _resolve_path(args.cache_path)
    rows = _load_rows(path)
    orgs = {
        str(row.get("org_name") or row.get("orgSName") or row.get("publisher") or "").strip()
        for row in rows
    }
    orgs.discard("")
    dates = sorted(
        {
            str(row.get("report_date") or row.get("publish_date") or row.get("source_date") or "").strip()
            for row in rows
            if str(row.get("report_date") or row.get("publish_date") or row.get("source_date") or "").strip()
        }
    )
    payload = {
        "command": "audit-forecast-source-count",
        "cache_path": str(path),
        "row_count": len(rows),
        "source_count": len(orgs),
        "org_names": sorted(orgs),
        "date_min": dates[0] if dates else "",
        "date_max": dates[-1] if dates else "",
        "status": "ok" if orgs else "missing_source_org",
        "note": "This is a source-count audit, not a consensus calculation.",
    }
    _emit(payload, args.format)
    return 0 if orgs else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    normalize = sub.add_parser("normalize-forecast-fields")
    normalize.add_argument("--project", default="")
    normalize.add_argument("--sector-id", default="")
    normalize.add_argument("--format", choices=["text", "json"], default="text")
    normalize.set_defaults(func=_normalize_fields)

    audit = sub.add_parser("audit-forecast-source-count")
    audit.add_argument("--cache-path", required=True)
    audit.add_argument("--format", choices=["text", "json"], default="text")
    audit.set_defaults(func=_audit_source_count)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
