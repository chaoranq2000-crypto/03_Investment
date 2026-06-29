"""Raw-cache and source-manifest helpers for Tushare data pulls."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from investment_system.core.constants import WORKSPACE_ROOT


def workspace_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(WORKSPACE_ROOT).as_posix()
    except ValueError:
        return str(path)


def safe_slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", text.strip()).strip("-") or "all"


def cache_path(dataset: str, run_date: str, target_key: str) -> Path:
    return (
        WORKSPACE_ROOT
        / "investment_system"
        / "data"
        / "raw"
        / "tushare"
        / dataset
        / run_date
        / f"{safe_slug(target_key)}.json"
    )


def manifest_path(project_id: str, sector_id: str, run_date: str) -> Path:
    return (
        WORKSPACE_ROOT
        / "investment_system"
        / "data"
        / "raw"
        / "tushare"
        / "source_manifests"
        / project_id
        / (sector_id or "no_sector")
        / run_date
        / f"source_manifest_tushare_{project_id}_{sector_id or 'no_sector'}_{run_date}.json"
    )


def build_envelope(
    *,
    dataset: str,
    api_name: str,
    group: str,
    project_id: str,
    sector_id: str,
    stock: dict[str, str],
    params: dict[str, Any],
    fields: str,
    rows: list[dict[str, Any]],
    row_limit: int,
    fetch_status: str,
    error: str = "",
) -> dict[str, Any]:
    return {
        "schema_version": "tushare_raw_cache.v1",
        "source": "tushare",
        "group": group,
        "dataset": dataset,
        "api_name": api_name,
        "project_id": project_id,
        "sector_id": sector_id,
        "stock": stock,
        "request": {
            "params": params,
            "fields": fields,
            "row_limit": row_limit,
        },
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "fetch_status": fetch_status,
        "error": error,
        "row_count": len(rows),
        "rows": rows,
        "notes": [
            "Raw API cache only; do not treat as curated evidence without source-manifest and evidence review.",
            "Private bridge configuration is intentionally omitted.",
        ],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_id_for(dataset: str, sector_id: str, target_key: str, run_date: str) -> str:
    compact_date = run_date.replace("-", "")
    subject = safe_slug(target_key).upper().replace(".", "-")
    sector = safe_slug(sector_id or "no_sector").upper()
    return f"TUSHARE-{safe_slug(dataset).upper()}-{sector}-{subject}-{compact_date}"


def build_manifest_record(
    *,
    project_id: str,
    sector_id: str,
    dataset: str,
    source_type: str,
    target_key: str,
    cache_file: Path,
    envelope: dict[str, Any],
) -> dict[str, Any]:
    payload_bytes = (json.dumps(envelope, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    run_date = str(cache_file.parent.name)
    stock = envelope.get("stock") if isinstance(envelope.get("stock"), dict) else {}
    company_code = str(stock.get("ts_code") or "")
    company_name = str(stock.get("stock_name") or stock.get("name") or "")
    return {
        "source_id": source_id_for(dataset, sector_id, target_key, run_date),
        "project_id": project_id,
        "sector_id": sector_id,
        "source_type": source_type,
        "evidence_level": "data_cache",
        "company_code": company_code,
        "company_name": company_name,
        "title": f"Tushare {dataset} raw cache for {target_key}",
        "publisher": "Tushare Pro",
        "source_date": run_date,
        "source_url": "",
        "local_path": workspace_relative(cache_file),
        "text_path": "",
        "file_sha256": sha256_bytes(payload_bytes),
        "file_size": len(payload_bytes),
        "access_method": "tushare_api",
        "parser": "tushare_data_router",
        "parser_status": str(envelope.get("fetch_status") or "unknown"),
        "metadata_sidecar_key": dataset,
        "metadata_missing_fields": [],
        "notes": "Generated from skill-owned Tushare raw cache. Curate manually before active evidence registration.",
    }


def write_manifest(path: Path, records: list[dict[str, Any]], project_id: str, sector_id: str, run_date: str) -> None:
    payload = {
        "manifest_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project_id": project_id,
        "sector_id": sector_id,
        "source_set": "tushare_raw_cache",
        "run_date": run_date,
        "record_count": len(records),
        "records": records,
    }
    write_json(path, payload)
