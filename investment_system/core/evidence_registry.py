"""Shared sector, stock, and evidence registry helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from investment_system.core.constants import WORKSPACE_ROOT

__all__ = [
    "build_legacy_sector_map",
    "get_sector",
    "get_stocks_for_sector",
    "list_scoring_sectors",
    "resolve_evidence_files_for_sector",
    "resolve_sector_id",
]


def build_legacy_sector_map(sectors: list[dict]) -> dict[str, str]:
    """
    Build reverse mapping: legacy_id -> canonical sector_id.
    Collects from legacy_sector_ids[], aliases[], and legacy_theme_names[].
    """
    legacy_map: dict[str, str] = {}
    for sector in sectors:
        sector_id = sector.get("sector_id", "")
        for legacy_id in sector.get("legacy_sector_ids", []):
            legacy_map[str(legacy_id)] = sector_id
        for alias in sector.get("aliases", []):
            legacy_map[str(alias)] = sector_id
        for legacy_theme_name in sector.get("legacy_theme_names", []):
            legacy_map[str(legacy_theme_name)] = sector_id
    return legacy_map


def resolve_sector_id(
    raw_id: str,
    valid_sector_ids: set[str],
    legacy_map: dict[str, str],
) -> tuple[str, bool]:
    """
    Resolve a sector ID that may be canonical or legacy.
    Returns (resolved_id, is_legacy).
    """
    if raw_id in valid_sector_ids:
        return raw_id, False
    if raw_id in legacy_map:
        return legacy_map[raw_id], True
    return raw_id, False


def _get_sector_by_id(config: Any, sector_id: str) -> dict[str, Any] | None:
    """Internal lookup: try canonical then legacy map."""
    sectors = config.raw.get("sectors", [])
    valid_ids = {s.get("sector_id") for s in sectors}
    legacy_map = config.raw.get("legacy_sector_map", {})

    resolved, _ = resolve_sector_id(sector_id, valid_ids, legacy_map)
    for sector in sectors:
        if sector.get("sector_id") == resolved:
            return sector
    return None


def get_sector(config: Any, sector_id_or_legacy: str) -> dict[str, Any]:
    """
    Look up a sector by canonical sector_id or legacy alias.

    Supports canonical sector_id, legacy_sector_ids[], aliases[], and
    legacy_theme_names[].
    """
    sector = _get_sector_by_id(config, sector_id_or_legacy)
    if sector is not None:
        return sector

    valid_ids = {
        s.get("sector_id")
        for s in config.raw.get("sectors", [])
        if s.get("sector_id")
    }
    raise KeyError(
        f"sector_id '{sector_id_or_legacy}' not found in sector_universe.yaml. "
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
    sector_id_or_legacy: str,
    *,
    include_pending: bool = False,
) -> list[dict[str, Any]]:
    """Return normalized stock records for a canonical sector or legacy alias."""
    sector = get_sector(config, sector_id_or_legacy)
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
    sector_id_or_legacy: str,
) -> list[dict[str, Any]]:
    """
    Return run_manifest evidence file records associated with a sector.

    The resolver ignores seed_documents and retired_legacy_outputs.
    """
    sector = get_sector(config, sector_id_or_legacy)
    canonical_id = sector.get("sector_id", "")
    evidence_file_ids = set(sector.get("evidence_file_ids", []) or [])

    evidence_files = config.raw.get("evidence_files", [])
    legacy_map = config.raw.get("legacy_sector_map", {})
    valid_ids = {
        s.get("sector_id")
        for s in config.raw.get("sectors", [])
        if s.get("sector_id")
    }
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
        legacy_sid = str(evidence_file.get("legacy_sector_id", "") or "")
        legacy_resolved = ""
        legacy_is_alias = False
        if legacy_sid:
            legacy_resolved, legacy_is_alias = resolve_sector_id(
                legacy_sid, valid_ids, legacy_map
            )
        return {
            "evidence_file_id": evidence_file.get("evidence_file_id", ""),
            "path": raw_path,
            "type": evidence_file.get("type", ""),
            "sector_id": canonical_id,
            "legacy_sector_id": legacy_sid,
            "status": evidence_file.get("status", ""),
            "action": evidence_file.get("action", ""),
            "exists": bool(raw_path and resolved_path.exists()),
            "notes": evidence_file.get("notes", ""),
            "_source": "run_manifest.yaml + sector_universe.yaml",
            "_match_type": match_type,
            "_manifest_sector_id": evidence_file.get("sector_id", ""),
            "_resolved_path": str(resolved_path),
            "_legacy_resolved_sector_id": legacy_resolved if legacy_is_alias else "",
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

        resolved, is_legacy = resolve_sector_id(evidence_sector_id, valid_ids, legacy_map)
        if is_legacy and resolved == canonical_id:
            _append_once(evidence_file, "legacy_sector_id")
            continue

    return result
