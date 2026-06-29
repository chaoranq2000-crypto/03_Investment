"""Shared sector, stock, and evidence registry helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from investment_system.core.constants import WORKSPACE_ROOT

__all__ = [
    "get_sector",
    "get_stocks_for_sector",
    "list_scoring_sectors",
    "resolve_evidence_files_for_sector",
]


def _get_sector_by_id(config: Any, sector_id: str) -> dict[str, Any] | None:
    """Internal lookup by canonical sector_id."""
    sectors = config.raw.get("sectors", [])
    for sector in sectors:
        if sector.get("sector_id") == sector_id:
            return sector
    return None


def get_sector(config: Any, sector_id: str) -> dict[str, Any]:
    """Look up a sector by canonical sector_id only."""
    sector = _get_sector_by_id(config, sector_id)
    if sector is not None:
        return sector

    valid_ids = {
        s.get("sector_id")
        for s in config.raw.get("sectors", [])
        if s.get("sector_id")
    }
    raise KeyError(
        f"sector_id '{sector_id}' not found in sector_universe.yaml. "
        f"Valid canonical IDs: {sorted(valid_ids)}"
    )


def list_scoring_sectors(config: Any) -> list[dict[str, Any]]:
    """Return all sectors where scoring_enabled=True."""
    return [
        sector for sector in config.raw.get("sectors", [])
        if sector.get("scoring_enabled", False)
    ]


def _normalize_stock_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Normalize stock_universe.yaml variants to a consistent dict shape."""
    code = entry.get("code", "")
    name = entry.get("name", code)
    status = entry.get("status") or entry.get("verification_status", "unverified")

    raw_sectors = entry.get("sectors") or entry.get("sector_ids") or entry.get("sector", [])
    if isinstance(raw_sectors, str):
        raw_sectors = [raw_sectors]

    role = entry.get("role", "")
    exposure = entry.get("exposure_type") or entry.get("exposure", "")

    return {
        "code": code,
        "name": name,
        "sectors": list(raw_sectors),
        "role": role,
        "exposure_type": exposure,
        "status": status,
        "notes": entry.get("notes", ""),
        "source": entry.get("source", ""),
        "_source": entry.get("_source", "stocks"),
        "pending": entry.get("pending", False),
    }


def _is_listed_stock(entry: dict[str, Any]) -> bool:
    """Return True if this entry represents a listed stock."""
    code = entry.get("code", "")
    return bool(code and code not in ("pending", "待查", ""))


def get_stocks_for_sector(
    config: Any,
    sector_id: str,
    *,
    include_pending: bool = False,
) -> list[dict[str, Any]]:
    """Return normalized stock records for a canonical sector."""
    sector = get_sector(config, sector_id)
    canonical_id = sector.get("sector_id", "")

    stocks_raw = config.raw.get("stocks", [])
    seen_keys: set[tuple[str, str]] = set()
    result: list[dict[str, Any]] = []

    for entry in stocks_raw:
        entry_sectors = entry.get("sectors", []) or entry.get("sector_ids", []) or []
        if canonical_id not in entry_sectors:
            continue
        if not _is_listed_stock(entry):
            continue
        normalized = _normalize_stock_entry(entry)
        dedup_key = (normalized["code"], canonical_id)
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)
        result.append(normalized)

    if include_pending:
        pending_raw = config.raw.get("stock_universe", {}).get("pending_code_resolution", [])
        for item in pending_raw:
            item_sectors = item.get("suggested_sectors", [])
            if canonical_id not in item_sectors:
                continue
            normalized = _normalize_stock_entry(item)
            normalized["pending"] = True
            normalized["_source"] = "pending"
            normalized["status"] = "pending_code_resolution"
            dedup_key = (normalized.get("name", ""), canonical_id)
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)
            result.append(normalized)

    return result


def resolve_evidence_files_for_sector(
    config: Any,
    sector_id: str,
) -> list[dict[str, Any]]:
    """
    Return run_manifest evidence file records associated with a sector.

    The resolver ignores seed_documents and retired_outputs.
    """
    sector = get_sector(config, sector_id)
    canonical_id = sector.get("sector_id", "")
    evidence_file_ids = set(sector.get("evidence_file_ids", []) or [])

    evidence_files = config.raw.get("evidence_files", [])
    result: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    def _resolve_path(raw_path: str) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path
        return WORKSPACE_ROOT / path

    def _normalize_record(evidence_file: dict[str, Any], match_type: str) -> dict[str, Any]:
        raw_path = str(evidence_file.get("path", ""))
        resolved_path = _resolve_path(raw_path) if raw_path else WORKSPACE_ROOT
        return {
            "evidence_file_id": evidence_file.get("evidence_file_id", ""),
            "path": raw_path,
            "type": evidence_file.get("type", ""),
            "sector_id": canonical_id,
            "status": evidence_file.get("status", ""),
            "action": evidence_file.get("action", ""),
            "exists": bool(raw_path and resolved_path.exists()),
            "notes": evidence_file.get("notes", ""),
            "_source": "run_manifest.yaml + sector_universe.yaml",
            "_match_type": match_type,
            "_manifest_sector_id": evidence_file.get("sector_id", ""),
            "_resolved_path": str(resolved_path),
        }

    def _append_once(evidence_file: dict[str, Any], match_type: str) -> None:
        evidence_file_id = str(evidence_file.get("evidence_file_id", "") or "")
        dedup_key = evidence_file_id or str(evidence_file.get("path", ""))
        if dedup_key in seen_ids:
            return
        seen_ids.add(dedup_key)
        result.append(_normalize_record(evidence_file, match_type))

    for evidence_file in evidence_files:
        evidence_sector_id = evidence_file.get("sector_id", "")
        evidence_file_id = evidence_file.get("evidence_file_id", "")

        if evidence_file_id and evidence_file_id in evidence_file_ids:
            _append_once(evidence_file, "evidence_file_id")
            continue

        if evidence_sector_id == canonical_id:
            _append_once(evidence_file, "canonical_sector_id")
            continue

    return result
