"""Shared sector runtime helpers for project-aware skill workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SectorContext:
    """Project-aware sector resolution result. Internal canonical form."""

    sector_id: str
    sector_name: str
    research_group_id: str
    group_name: str
    group_order: str
    priority: str
    chain_position: str
    parent_chain: str
    industry_logic: str
    scoring_enabled: bool
    aliases: list[str]
    input_raw: str
    canonical_sector_id: str = field(init=False)

    def __post_init__(self) -> None:
        self.canonical_sector_id = self.sector_id


@dataclass
class ResearchRuntimePaths:
    """Injected path context for project-aware mode. Never touches globals."""

    output_root: Path
    total_tables_dir: Path
    logs_dir: Path
    raw_data_root: Path
    source_index_path: Path
    missing_data_log_path: Path
    conflict_data_log_path: Path
    research_log_path: Path
    _resolve_sector_card_path = None

    def resolve_sector_card_path(self, sector_or_id):
        if self._resolve_sector_card_path is None:
            raise RuntimeError(
                "resolve_sector_card_path not set in project-aware mode. "
                "Ensure the project-aware runtime branch initialized it."
            )
        return self._resolve_sector_card_path(sector_or_id)


def safe_output_name(value: str) -> str:
    """Return a filesystem-safe display-name preserving Chinese text."""
    return (
        value.replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
        .replace("*", "_")
        .replace("?", "_")
        .replace('"', "_")
        .replace("<", "_")
        .replace(">", "_")
        .replace("|", "_")
    )


def resolve_sector_context(
    config: Any,
    sector_id: str,
    loader_module: Any | None = None,
) -> SectorContext:
    """Resolve a canonical sector_id into a SectorContext."""
    sectors = config.raw.get("sectors", [])
    research_groups = config.raw.get("research_groups", [])
    valid_ids = {s.get("sector_id") for s in sectors}

    if sector_id not in valid_ids:
        raise KeyError(
            f"Cannot resolve sector '{sector_id}'. "
            "Only canonical sector_id values are accepted. "
            f"Valid canonical IDs: {sorted(valid_ids)}"
        )

    sector_dict = None
    for sector in sectors:
        if sector.get("sector_id") == sector_id:
            sector_dict = sector
            break

    if sector_dict is None:
        raise KeyError(
            f"sector_id '{sector_id}' is listed as valid but the sector record was not found."
        )

    research_group_id = sector_dict.get("research_group_id", "")
    group_dict = None
    for group in research_groups:
        if group.get("group_id") == research_group_id:
            group_dict = group
            break

    group_name = group_dict.get("group_name", "") if group_dict else ""

    return SectorContext(
        sector_id=sector_id,
        sector_name=sector_dict.get("sector_name", sector_id),
        research_group_id=research_group_id,
        group_name=group_name,
        group_order=str(sector_dict.get("group_order", "99")),
        priority=sector_dict.get("priority", "P9"),
        chain_position=sector_dict.get("chain_position", "待确认"),
        parent_chain=sector_dict.get("parent_chain", "AI算力硬件"),
        industry_logic=sector_dict.get("industry_logic", ""),
        scoring_enabled=sector_dict.get("scoring_enabled", False),
        aliases=list(sector_dict.get("aliases", [])),
        input_raw=sector_id,
    )


def list_project_sectors_by_priority(
    config: Any,
    priority_filter: str | None,
    loader_module: Any | None = None,
) -> list[SectorContext]:
    """Return project sectors, optionally filtered by p0/p1/p2/all."""
    priority_map = {"p0": "P0", "p1": "P1", "p2": "P2", "all": None}
    target = priority_map.get(priority_filter)
    result: list[SectorContext] = []
    for sector in config.raw.get("sectors", []):
        sector_id = sector.get("sector_id", "")
        if not sector_id:
            continue
        if target and sector.get("priority", "P9") != target:
            continue
        result.append(resolve_sector_context(config, sector_id, loader_module))
    return result


def compute_coverage_status(ctx: SectorContext, stock_count: int) -> dict[str, Any]:
    """Return project-aware stock coverage status without collecting data."""
    if ctx.research_group_id == "peripheral_observation":
        return {"status": "exempt", "required": 0, "warning": ""}

    if ctx.priority in ("P0", "P1"):
        required = 5
        rule_label = f"{ctx.priority} sector"
    elif ctx.scoring_enabled:
        required = 3
        rule_label = f"{ctx.priority} scoring_enabled sector"
    else:
        required = 0
        rule_label = "non-scoring sector"

    if stock_count == 0:
        if required:
            return {
                "status": "missing",
                "required": required,
                "warning": (
                    f"{rule_label} requires at least {required} listed stocks, "
                    "currently 0."
                ),
            }
        return {
            "status": "missing",
            "required": 0,
            "warning": "No listed stocks found; coverage threshold is not enforced for this sector.",
        }

    if required and stock_count < required:
        return {
            "status": "thin",
            "required": required,
            "warning": (
                f"{rule_label} requires at least {required} listed stocks, "
                f"currently {stock_count}."
            ),
        }

    return {"status": "ok", "required": required, "warning": ""}


def check_path_safety(path_str: str) -> None:
    """Reject unresolved output-template placeholders."""
    for placeholder in (
        "{group_order}",
        "{group_name}",
        "{sector_name_safe}",
        "{priority}",
        "{group_id}",
        "{sector_id}",
    ):
        if placeholder in path_str:
            raise ValueError(
                f"Unresolved placeholder '{placeholder}' found in output path: {path_str}. "
                "Fix the path template in output_spec.yaml or sector_universe.yaml."
            )
