"""Shared path-resolution helpers for project-aware workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = [
    "resolve_output_paths",
    "resolve_sector_card_path",
    "safe_filename",
]


def safe_filename(s: str) -> str:
    """Convert a string to a safe filename while preserving readable text."""
    s = s.replace("/", "_").replace("\\", "_")
    s = s.replace(":", "_").replace("*", "_")
    s = s.replace("?", "_").replace('"', "_")
    s = s.replace("<", "_").replace(">", "_")
    s = s.replace("|", "_").replace(" ", "_")
    return s


def _resolve_sector_id(raw_id: str, valid_sector_ids: set[str], legacy_map: dict[str, str]) -> str:
    if raw_id in valid_sector_ids:
        return raw_id
    return legacy_map.get(raw_id, raw_id)


def _get_sector_by_id(config: Any, sector_id: str) -> dict[str, Any] | None:
    sectors = config.raw.get("sectors", [])
    valid_ids = {s.get("sector_id") for s in sectors}
    legacy_map = config.raw.get("legacy_sector_map", {})

    resolved = _resolve_sector_id(sector_id, valid_ids, legacy_map)
    for sector in sectors:
        if sector.get("sector_id") == resolved:
            return sector
    return None


def resolve_sector_card_path(
    config: Any,
    sector_or_id: dict[str, Any] | str,
    output_spec: dict[str, Any] | None = None,
) -> Path:
    """Resolve the expected sector card path without creating files."""
    if isinstance(sector_or_id, str):
        sector_dict = _get_sector_by_id(config, sector_or_id)
        if sector_dict is None:
            raise ValueError(
                f"sector_id '{sector_or_id}' not found in sector_universe.yaml "
                f"(checked legacy aliases as well)"
            )
    else:
        sector_dict = sector_or_id

    if output_spec is None:
        output_spec = config.raw.get("output_spec", {})

    dirs = output_spec.get("directories", {})
    sc_cfg = dirs.get("sector_cards", {})
    path_template = sc_cfg.get("path_template", "{group_order}_{group_name}")
    filename_pattern = sc_cfg.get(
        "filename_pattern", "{priority}_{sector_name_safe}.md"
    )

    research_groups = config.raw.get("research_groups", [])
    rg_id = sector_dict.get("research_group_id", "")
    group_order = str(sector_dict.get("group_order", "99"))
    group_name = ""
    for group in research_groups:
        if group.get("group_id") == rg_id:
            group_name = group.get("group_name", "")
            break

    group_dir = (
        path_template
        .replace("{group_order}", group_order)
        .replace("{group_name}", group_name)
    )

    sector_name = sector_dict.get("sector_name", "")
    priority = sector_dict.get("priority", "P9")
    sector_name_safe = safe_filename(sector_name)
    filename = (
        filename_pattern
        .replace("{priority}", priority)
        .replace("{sector_name_safe}", sector_name_safe)
    )

    return config.sector_cards_root / group_dir / filename


def resolve_output_paths(
    config: Any,
    sector_id_or_legacy: str | None = None,
) -> dict[str, Any]:
    """Resolve shared and optional sector-specific output paths without writing."""
    output_spec = config.raw.get("output_spec", {})
    dirs = output_spec.get("directories", {})

    result: dict[str, Any] = {
        "output_root": str(config.output_root),
        "sector_cards_root": str(config.sector_cards_root),
        "total_tables_dir": str(config.total_tables_dir),
        "logs_dir": str(config.logs_dir),
        "raw_data_root": str(config.raw_data_root),
    }

    tt_cfg = dirs.get("total_tables", {})
    if isinstance(tt_cfg, dict):
        for file_def in tt_cfg.get("files", []):
            fname = file_def.get("name", "?")
            result[f"table_{fname}"] = str(config.total_tables_dir / fname)
        result["source_index_path"] = str(config.total_tables_dir / "数据来源索引.csv")
        result["company_table_path"] = str(config.total_tables_dir / "代表公司财务估值总表.csv")
        result["comparison_table_path"] = str(config.total_tables_dir / "科技细分方向横向比较表.csv")

    lg_cfg = dirs.get("logs", {})
    if isinstance(lg_cfg, dict):
        for file_def in lg_cfg.get("files", []):
            fname = file_def.get("name", "?")
            result[f"log_{fname}"] = str(config.logs_dir / fname)
        result["missing_data_log_path"] = str(config.logs_dir / "缺失数据清单.md")
        result["conflict_data_log_path"] = str(config.logs_dir / "冲突数据清单.md")
        result["research_log_path"] = str(config.logs_dir / "调研日志.md")

    if sector_id_or_legacy:
        sector = _get_sector_by_id(config, sector_id_or_legacy)
        if sector:
            sector_id = sector.get("sector_id", sector_id_or_legacy)
            result["sector_id_resolved"] = sector_id
            result["sector_card_path"] = str(resolve_sector_card_path(config, sector, output_spec))

            raw_cfg = dirs.get("raw_data", {})
            if isinstance(raw_cfg, dict):
                raw_path_template = raw_cfg.get(
                    "path_template", "00_原始数据/{sector_name_safe}"
                )
                sector_name_safe = safe_filename(sector.get("sector_name", sector_id))
                raw_subdir = raw_path_template.replace(
                    "{sector_name_safe}", sector_name_safe
                )
                result["raw_data_dir"] = str(config.output_root / raw_subdir)

    return result
