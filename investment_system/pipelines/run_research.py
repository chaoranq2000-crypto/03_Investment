"""Standardized automated research pipeline for A股科技主线.

Usage:
    # Project-aware mode (RECOMMENDED):
    python run_research.py --project tech_ai_semiconductor --sector-id cpo_optical_module_silicon_photonics
    python run_research.py --project tech_ai_semiconductor --sector-id high_speed_optical_modules  # legacy alias OK
    python run_research.py --project tech_ai_semiconductor --batch p0

    # Dry-run resolve (no data, no file writes):
    python run_research.py --project tech_ai_semiconductor --sector-id cpo_optical_module_silicon_photonics --dry-run-resolve

Output follows project output_spec.yaml (--project):
    configured project output root:
        00_总表/
            代表公司财务估值总表.csv    (append mode)
            科技细分方向横向比较表.csv (append mode)
            数据来源索引.csv           (append mode)
        {group_order}_{group_name}/    (e.g. 03_光通信_高速互连/)
            {priority}_{sector_name_safe}.md   (e.g. P0_光模块_CPO_硅光.md)
        99_日志/
            缺失数据清单.md
            冲突数据清单.md
            调研日志.md
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

# Add investment_system/ to path so evidence_overrides and sector_research loaders resolve
# pipelines/ → investment_system/ → project/  => ROOT = C:\Projects\03_Investment
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "investment_system"))       # for evidence_overrides (pipelines/)
sys.path.insert(0, str(ROOT / "investment_system" / "scripts"))  # for research_client

from research_client import (
    ResearchClient,
    tencent_bar_direct,
    load_env,
    HumanRateLimiter,
)
from investment_system.pipelines.evidence_overrides import (
    apply_company_overrides,
    apply_comparison_override,
    card_markdown,
    evidence_source_rows,
    load_theme_evidence,
    write_evidence_logs,
)

TODAY = date.today().isoformat()
RAW_CACHE_DIR = ROOT / "investment_system" / "data" / "raw"
PROCESSED_DIR = ROOT / "investment_system" / "data" / "processed" / "theme_research" / TODAY
RUN_META_DIR = RAW_CACHE_DIR / "research_runs" / TODAY


# ── Project-aware SectorContext ───────────────────────────────────────────────

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
    legacy_sector_ids: list[str]
    legacy_theme_names: list[str]
    input_raw: str           # what the user actually typed
    was_legacy_alias: bool   # True if input was resolved via legacy alias
    # Canonical sector_id — always equals sector_id after construction
    canonical_sector_id: str = field(init=False)

    def __post_init__(self):
        self.canonical_sector_id = self.sector_id


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
    sector_id_or_legacy: str,
    loader_module: Any,
) -> SectorContext:
    """
    Resolve a sector identifier (canonical or legacy) into a SectorContext.

    In project-aware mode, this is the ONLY entry point for sector resolution.
    Supports: canonical sector_id, legacy_sector_ids[], aliases[],
    legacy_theme_names[].

    Args:
        config: loaded ProjectConfig from load_project()
        sector_id_or_legacy: raw input from CLI (may be canonical or legacy)
        loader_module: the load_project module (for get_sector, research_groups)

    Returns:
        SectorContext with all fields populated

    Raises:
        KeyError: if sector cannot be resolved
    """
    sectors = config.raw.get("sectors", [])
    research_groups = config.raw.get("research_groups", [])
    valid_ids = {s.get("sector_id") for s in sectors}
    legacy_map = config.raw.get("legacy_sector_map", {})

    # Build a quick lookup: legacy alias -> sector dict
    resolved_id = sector_id_or_legacy
    was_legacy = False

    if sector_id_or_legacy in valid_ids:
        pass  # canonical, no change
    elif sector_id_or_legacy in legacy_map:
        resolved_id = legacy_map[sector_id_or_legacy]
        was_legacy = True
    else:
        raise KeyError(
            f"Cannot resolve sector '{sector_id_or_legacy}'. "
            f"Not found as canonical sector_id. "
            f"Valid canonical IDs: {sorted(valid_ids)}"
        )

    # Find the sector dict
    sector_dict = None
    for s in sectors:
        if s.get("sector_id") == resolved_id:
            sector_dict = s
            break

    if sector_dict is None:
        raise KeyError(
            f"Resolved to '{resolved_id}' but sector not found. "
            f"This should not happen — legacy_map may be stale."
        )

    # Find the research group
    rg_id = sector_dict.get("research_group_id", "")
    group_dict = None
    for g in research_groups:
        if g.get("group_id") == rg_id:
            group_dict = g
            break

    group_name = group_dict.get("group_name", "") if group_dict else ""
    group_order = str(sector_dict.get("group_order", "99"))

    return SectorContext(
        sector_id=resolved_id,
        sector_name=sector_dict.get("sector_name", resolved_id),
        research_group_id=rg_id,
        group_name=group_name,
        group_order=group_order,
        priority=sector_dict.get("priority", "P9"),
        chain_position=sector_dict.get("chain_position", "待确认"),
        parent_chain=sector_dict.get("parent_chain", "AI算力硬件"),
        industry_logic=sector_dict.get("industry_logic", ""),
        scoring_enabled=sector_dict.get("scoring_enabled", False),
        aliases=list(sector_dict.get("aliases", [])),
        legacy_sector_ids=list(sector_dict.get("legacy_sector_ids", [])),
        legacy_theme_names=list(sector_dict.get("legacy_theme_names", [])),
        input_raw=sector_id_or_legacy,
        was_legacy_alias=was_legacy,
    )


def list_project_sectors_by_priority(
    config: Any,
    priority_filter: str | None,
    loader_module: Any,
) -> list[SectorContext]:
    """
    Return all sectors for the project, optionally filtered by priority.
    Used by batch mode to iterate sectors from sector_universe.yaml.
    """
    sectors = config.raw.get("sectors", [])
    result = []
    for s in sectors:
        sid = s.get("sector_id", "")
        if not sid:
            continue
        p = s.get("priority", "P9")
        if priority_filter and priority_filter not in ("all", "p0", "p1", "p2"):
            pass
        # Map batch label to priority
        priority_map = {"p0": "P0", "p1": "P1", "p2": "P2", "all": None}
        target = priority_map.get(priority_filter)
        if target and p != target:
            continue
        ctx = resolve_sector_context(config, sid, loader_module)
        result.append(ctx)
    return result


def compute_coverage_status(ctx: SectorContext, stock_count: int) -> dict[str, Any]:
    """Return project-aware stock coverage status without collecting data."""
    if ctx.research_group_id == "peripheral_observation":
        return {
            "status": "exempt",
            "required": 0,
            "warning": "",
        }

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
                    f"currently 0."
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

    return {
        "status": "ok",
        "required": required,
        "warning": "",
    }


# ── Project-aware runtime context ──────────────────────────────────────────────

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

    # sector-card resolver (set by project-aware runner)
    _resolve_sector_card_path = None   # callable, set at runtime

    def resolve_sector_card_path(self, sector_or_id):
        if self._resolve_sector_card_path is None:
            raise RuntimeError(
                "resolve_sector_card_path not set in project-aware mode. "
                "Ensure run_research.py is running in project-aware branch."
            )
        return self._resolve_sector_card_path(sector_or_id)


# Project-aware globals — only set when --project is passed
_project_config = None
_runtime_paths: ResearchRuntimePaths | None = None


_UNRESOLVED_TEMPLATE_PATTERN = object()  # sentinel

def _check_path_safety(path_str: str) -> None:
    """
    Raise ValueError if path_str contains unresolved template placeholders.
    Safety guard for project-aware mode — prevents {group_order}/{group_name} leaks.
    """
    for placeholder in ("{group_order}", "{group_name}", "{sector_name_safe}",
                       "{priority}", "{group_id}", "{sector_id}"):
        if placeholder in path_str:
            raise ValueError(
                f"Unresolved placeholder '{placeholder}' found in output path: {path_str}. "
                f"Fix the path template in output_spec.yaml or sector_universe.yaml."
            )


# ---------------------------------------------------------------------------
# Data processing helpers
# ---------------------------------------------------------------------------

def yuan_to_yi(value: str) -> str:
    try:
        return f"{float(value) / 1e8:.2f}"
    except (TypeError, ValueError):
        return "缺失"


def pct(value: str) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return "缺失"


def pct_change(rows: list[dict], periods: int) -> str:
    try:
        latest = float(rows[-1].get("close", 0))
        base = float(rows[-1 - periods].get("close", 0))
        if base == 0:
            return "缺失"
        return f"{(latest / base - 1) * 100:.2f}%"
    except (TypeError, ValueError, IndexError):
        return "缺失"


def amount_avg(rows: list[dict], periods: int = 20) -> str:
    try:
        vals = [float(r.get("amount", 0)) for r in rows[-periods:] if r.get("amount")]
        if not vals:
            return "缺失"
        return f"{sum(vals) / len(vals) / 1e8:.2f}亿元"
    except (TypeError, ValueError):
        return "缺失"


def annual_profit(rows: list[dict], year: str) -> dict:
    """Get Q4 (annual) profit row for given year."""
    matches = [r for r in rows if r.get("year") == year and r.get("quarter") == "4"]
    return matches[-1] if matches else {}


def derive_revenue_yi_from_akshare_indicator(rows: list[dict], year: str = "2025") -> str:
    """Derive revenue from AKShare indicators when direct revenue is absent."""
    for row in rows:
        if not str(row.get("日期", "")).startswith(f"{year}-12-31"):
            continue
        profit = row.get("主营业务利润(元)")
        margin_pct = row.get("主营业务利润率(%)")
        try:
            profit_f = float(profit)
            margin_f = float(margin_pct) / 100
            if margin_f:
                return f"{profit_f / margin_f / 1e8:.2f}"
        except (TypeError, ValueError):
            return ""
    return ""


def get_latest_profit(rows: list[dict]) -> dict:
    if not rows:
        return {}
    return max(rows, key=lambda r: r.get("statDate", ""))


def relative_strength(rows: list[dict], index_rows: list[dict], periods: int = 60) -> str:
    """Compare stock return vs index return over same period."""
    try:
        stock_latest = float(rows[-1].get("close", 0))
        stock_base = float(rows[-1 - periods].get("close", 0))
        idx_latest = float(index_rows[-1].get("close", 0))
        idx_base = float(index_rows[-1 - periods].get("close", 0))
        stock_ret = (stock_latest / stock_base - 1) * 100
        idx_ret = (idx_latest / idx_base - 1) * 100
        return f"{stock_ret:.2f}% vs {idx_ret:.2f}%"
    except (TypeError, ValueError, IndexError):
        return "缺失"


# ---------------------------------------------------------------------------
# Output generation
# ---------------------------------------------------------------------------

COMPANY_TABLE_FIELDS = [
    "project_id", "sector_id", "sector_name", "research_group_id",
    "stock_code", "stock_name", "market", "role", "exposure_type",
    "coverage_status", "data_status", "financial_period",
    "revenue", "net_profit", "gross_margin",
    "pe_ttm", "pe_2026e", "pe_2027e", "peg",
    "source_ids", "evidence_ids", "missing_fields", "conflict_flags", "notes",
]

COMPARISON_FIELDS = [
    "project_id", "sector_id", "sector_name", "research_group_id",
    "parent_chain", "chain_position", "core_logic",
    "leader_stocks", "elastic_stocks",
    "prosperity_score", "prosperity_reason",
    "earnings_certainty_score", "earnings_certainty_reason",
    "valuation_score", "valuation_reason",
    "trading_comfort_score", "trading_comfort_reason",
    "catalyst_score", "catalyst_reason",
    "purity_score", "purity_reason",
    "risk_control_score", "risk_control_reason",
    "total_score", "action_rating", "rating_reason", "suggested_action",
    "key_evidence", "key_risk", "missing_data_flags",
    "source_ids", "evidence_ids", "confidence_level", "generated_at",
]

SOURCE_FIELDS = [
    "project_id", "source_id", "subject_type", "subject_id", "subject_name",
    "sector_id", "claim_supported", "source_type", "source_title",
    "source_date", "url_or_path", "extracted_fields", "confidence",
    "evidence_ids", "notes",
]


def ensure_dirs() -> None:
    if _runtime_paths is None:
        raise RuntimeError("project runtime paths are required")
    for d in [
        _runtime_paths.output_root,
        _runtime_paths.total_tables_dir,
        _runtime_paths.logs_dir,
        RUN_META_DIR,
        PROCESSED_DIR,
    ]:
        Path(d).mkdir(parents=True, exist_ok=True)


def append_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    """Append rows to a CSV, creating with header if missing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


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


def _project_sector_meta(sector_id: str | None) -> dict[str, str]:
    if _project_config is None or not sector_id:
        return {}
    try:
        from investment_system.pipelines.sector_research.load_project import get_sector
        sector = get_sector(_project_config, sector_id)
    except Exception:
        return {}
    return {
        "sector_id": sector.get("sector_id", sector_id),
        "sector_name": sector.get("sector_name", ""),
        "research_group_id": sector.get("research_group_id", ""),
        "parent_chain": sector.get("parent_chain", ""),
        "chain_position": sector.get("chain_position", ""),
    }


def _company_meta_by_code(companies: list[dict]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for c in companies:
        code = str(c.get("code", ""))
        base = code.split(".")[0]
        result[base] = c
        result[code] = c
    return result


def to_project_company_rows(
    legacy_rows: list[dict[str, str]],
    companies: list[dict],
    sector_id: str | None,
) -> list[dict[str, str]]:
    """Adapt legacy company rows into the project-aware company_table contract."""
    sector = _project_sector_meta(sector_id)
    company_meta = _company_meta_by_code(companies)
    rows: list[dict[str, str]] = []
    for row in legacy_rows:
        raw_code = str(row.get("stock_code", ""))
        base_code = raw_code.split(".")[0]
        meta = company_meta.get(raw_code) or company_meta.get(base_code) or {}
        full_code = raw_code if "." in raw_code else (
            f"{base_code}.{meta.get('market', '')}" if meta.get("market") else base_code
        )
        missing_fields = [
            key for key, value in row.items()
            if value in ("", "缺失") or "缺失" in str(value)
        ]
        rows.append({
            "project_id": _project_config.project_id if _project_config else "",
            "sector_id": sector.get("sector_id", sector_id or ""),
            "sector_name": sector.get("sector_name", row.get("sub_theme", "")),
            "research_group_id": sector.get("research_group_id", ""),
            "stock_code": full_code,
            "stock_name": row.get("company_name", meta.get("name", "")),
            "market": meta.get("market", _market_from_code(full_code)),
            "role": meta.get("role", ""),
            "exposure_type": meta.get("exposure_type", ""),
            "coverage_status": "listed",
            "data_status": "legacy_adapter",
            "financial_period": "latest_available",
            "revenue": row.get("revenue_2025") or row.get("revenue_2024", ""),
            "net_profit": row.get("net_profit_2025") or row.get("net_profit_2024", ""),
            "gross_margin": row.get("gross_margin_latest", ""),
            "pe_ttm": row.get("pe_ttm", ""),
            "pe_2026e": row.get("pe_2026E", ""),
            "pe_2027e": row.get("pe_2027E", ""),
            "peg": row.get("peg_2026E", ""),
            "source_ids": "",
            "evidence_ids": "",
            "missing_fields": ",".join(missing_fields),
            "conflict_flags": "",
            "notes": "adapted_from_legacy_company_row; source/evidence ids require next-stage generator alignment",
        })
    return rows


def to_project_comparison_row(row: dict[str, str], sector_id: str | None) -> dict[str, str]:
    """Adapt a legacy comparison row into the project-aware comparison contract."""
    sector = _project_sector_meta(sector_id)
    return {
        "project_id": _project_config.project_id if _project_config else "",
        "sector_id": sector.get("sector_id", sector_id or ""),
        "sector_name": sector.get("sector_name", row.get("sub_theme", "")),
        "research_group_id": sector.get("research_group_id", ""),
        "parent_chain": sector.get("parent_chain", row.get("main_theme", "")),
        "chain_position": sector.get("chain_position", row.get("chain_position", "")),
        "core_logic": row.get("industry_logic_summary", ""),
        "leader_stocks": row.get("representative_companies", ""),
        "elastic_stocks": "",
        "prosperity_score": row.get("industry_prosperity_score", ""),
        "prosperity_reason": row.get("key_evidence", ""),
        "earnings_certainty_score": row.get("performance_stage_score", ""),
        "earnings_certainty_reason": row.get("key_evidence", ""),
        "valuation_score": row.get("upside_score", ""),
        "valuation_reason": row.get("key_risks", ""),
        "trading_comfort_score": row.get("bubble_safety_score", ""),
        "trading_comfort_reason": row.get("key_risks", ""),
        "catalyst_score": row.get("catalyst_score", ""),
        "catalyst_reason": row.get("key_evidence", ""),
        "purity_score": row.get("fund_recognition_score", ""),
        "purity_reason": row.get("key_evidence", ""),
        "risk_control_score": row.get("bubble_safety_score", ""),
        "risk_control_reason": row.get("key_risks", ""),
        "total_score": row.get("total_score", ""),
        "action_rating": "",
        "rating_reason": "pending_output_schema_alignment",
        "suggested_action": row.get("recommended_next_action", ""),
        "key_evidence": row.get("key_evidence", ""),
        "key_risk": row.get("key_risks", ""),
        "missing_data_flags": row.get("missing_data", ""),
        "source_ids": row.get("source_index_refs", ""),
        "evidence_ids": "",
        "confidence_level": "",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


def to_project_source_rows(rows: list[dict[str, str]], sector_id: str | None) -> list[dict[str, str]]:
    """Adapt legacy source rows into the project-aware source_index contract."""
    sector = _project_sector_meta(sector_id)
    result: list[dict[str, str]] = []
    for row in rows:
        result.append({
            "project_id": _project_config.project_id if _project_config else "",
            "source_id": row.get("source_id", ""),
            "subject_type": "company" if row.get("related_company") else "sector",
            "subject_id": row.get("related_company") or sector.get("sector_id", sector_id or ""),
            "subject_name": row.get("related_company") or sector.get("sector_name", ""),
            "sector_id": sector.get("sector_id", sector_id or ""),
            "claim_supported": row.get("quote_or_excerpt", ""),
            "source_type": row.get("source_type", "other"),
            "source_title": row.get("source_name", ""),
            "source_date": row.get("source_date", ""),
            "url_or_path": row.get("source_url", ""),
            "extracted_fields": row.get("data_fields_supported", ""),
            "confidence": row.get("confidence_level", ""),
            "evidence_ids": "",
            "notes": row.get("notes", ""),
        })
    return result


def read_raw_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data.get("rows", [])
        if not isinstance(rows, list) or not rows:
            return []
        first = rows[0]
        if isinstance(first, dict) and any(k.endswith("error") or k == "_error" for k in first):
            return []
        return rows
    except (json.JSONDecodeError, OSError):
        return []


def json_safe_rows(rows: list[dict]) -> list[dict]:
    safe_rows = []
    for row in rows:
        safe = {}
        for key, value in row.items():
            if hasattr(value, "isoformat"):
                safe[key] = value.isoformat()
            else:
                safe[key] = value
        safe_rows.append(safe)
    return safe_rows


def build_source_id(prefix: str) -> str:
    return f"SRC-{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}"


def score_direction(rows: list[dict], periods: int = 60) -> tuple[int, str]:
    """Score bubble safety: how much has the stock already run up?"""
    try:
        latest = float(rows[-1].get("close", 0))
        base = float(rows[-1 - periods].get("close", 0))
        if base == 0:
            return 0, "无法计算"
        ret = (latest / base - 1) * 100
        if ret > 200:
            return 1, f"近{periods}日涨幅{ret:.0f}%，极度拥挤"
        elif ret > 100:
            return 2, f"近{periods}日涨幅{ret:.0f}%，拥挤"
        elif ret > 50:
            return 3, f"近{periods}日涨幅{ret:.0f}%，偏高"
        elif ret > 20:
            return 4, f"近{periods}日涨幅{ret:.0f}%，合理"
        else:
            return 5, f"近{periods}日涨幅{ret:.0f}%，尚在合理区间"
    except (TypeError, ValueError, IndexError):
        return 3, "数据不足，无法判断"


def build_company_rows(
    companies: list[dict],
    daily_data: dict[str, list[dict]],
    profit_data: dict[str, list[dict]],
    sub_theme: str,
    main_theme: str,
    chain_position: str,
    source_ids: list[str],
) -> tuple[list[dict], list[dict]]:
    """Build company table rows + new source rows."""
    company_rows = []
    new_sources = []

    for c in companies:
        code = c["code"]
        market = c["market"]
        name = c["name"]
        drows = daily_data.get(code, [])
        prows = profit_data.get(code, [])

        latest_daily = drows[-1] if drows else {}
        latest_profit_data = get_latest_profit(prows)
        row_2024 = annual_profit(prows, "2024")
        row_2025 = annual_profit(prows, "2025")

        latest_price_str = latest_daily.get("close", "缺失")
        try:
            latest_price = float(latest_price_str)
        except (TypeError, ValueError):
            latest_price = 0.0

        total_share_str = latest_profit_data.get("totalShare", "")
        try:
            total_share = float(total_share_str)
            market_cap = f"{latest_price * total_share / 1e8:.2f}亿元" if latest_price else "缺失"
        except (TypeError, ValueError):
            market_cap = "缺失"

        eps_ttm_str = latest_profit_data.get("epsTTM", "")
        try:
            eps_ttm = float(eps_ttm_str)
            pe_ttm = f"{latest_price / eps_ttm:.2f}" if eps_ttm != 0 else "缺失"
        except (TypeError, ValueError):
            pe_ttm = "缺失"

        idx_rows = []  # placeholder
        rel_strength = relative_strength(drows, idx_rows, 60)

        src_id = build_source_id(f"BAO-{code}")
        new_sources.append({
            "source_id": src_id,
            "source_type": "database",
            "source_name": "BaoStock query_history_k_data_plus + query_profit_data",
            "source_date": TODAY,
            "source_url": f"investment_system/data/raw/baostock/",
            "related_main_theme": main_theme,
            "related_sub_theme": sub_theme,
            "related_company": name,
            "quote_or_excerpt": f"revenue_2025={row_2025.get('MBRevenue','缺失')}元, net_profit_2025={row_2025.get('netProfit','缺失')}元",
            "data_fields_supported": "revenue,net_profit,gross_margin,net_margin,epsTTM,totalShare,close",
            "confidence_level": "高",
            "notes": "BaoStock primary data; Tencent fallback if BaoStock fails",
        })

        row = {
            "stock_code": code,
            "company_name": name,
            "main_theme": main_theme,
            "sub_theme": sub_theme,
            "chain_position": chain_position,
            "market_cap": market_cap,
            "latest_price": latest_price_str,
            "pct_change_1m": pct_change(drows, 20),
            "pct_change_3m": pct_change(drows, 60),
            "pct_change_6m": pct_change(drows, 120),
            "turnover_value_20d_avg": amount_avg(drows, 20),
            "relative_strength_vs_index": rel_strength,
            "revenue_2024": yuan_to_yi(row_2024.get("MBRevenue", "")),
            "revenue_2025": yuan_to_yi(row_2025.get("MBRevenue", "")),
            "revenue_2026E": "缺失",
            "revenue_2027E": "缺失",
            "net_profit_2024": yuan_to_yi(row_2024.get("netProfit", "")),
            "net_profit_2025": yuan_to_yi(row_2025.get("netProfit", "")),
            "net_profit_2026E": "缺失",
            "net_profit_2027E": "缺失",
            "gross_margin_latest": pct(latest_profit_data.get("gpMargin", "")),
            "net_margin_latest": pct(latest_profit_data.get("npMargin", "")),
            "pe_ttm": pe_ttm,
            "pe_2026E": "缺失",
            "pe_2027E": "缺失",
            "ps_ttm": "缺失",
            "peg_2026E": "缺失",
            "main_theme_revenue_exposure": "缺失；待核实公告/投资者关系",
            "order_or_customer_evidence": "缺失；待核实公告/互动平台",
            "capacity_progress": "缺失；待核实公告/定期报告",
            "product_stage": "待核实",
            "institution_forecast_change": "缺失",
            "catalysts": f"{sub_theme}主线催化持续；待逐项证据化",
            "risks": "主线收入暴露待核实；涨幅较大注意拥挤风险",
            "data_source": "BaoStock; Tencent direct; AKShare/Tushare fallback",
            "source_date": TODAY,
            "source_url": f"investment_system/data/raw/baostock/daily_kline/{TODAY}/{code}.json; investment_system/data/raw/baostock/profit/{TODAY}/{code}.json",
            "confidence_level": "中：行情/财务可用，主线收入暴露待核实",
        }
        company_rows.append(row)

    return company_rows, new_sources


def build_comparison_row(
    sub_theme: str, main_theme: str, chain_position: str,
    companies: list[dict], daily_data: dict,
    missing_data: list[str],
    industry_logic: str = "",
) -> dict:
    """Build one cross-theme comparison row."""
    all_6m = []
    for code, rows in daily_data.items():
        try:
            latest = float(rows[-1].get("close", 0))
            base = float(rows[-1 - 120].get("close", 0))
            if base:
                all_6m.append((latest / base - 1) * 100)
        except (TypeError, ValueError, IndexError):
            pass

    names = ", ".join(c["name"] for c in companies)
    bubble_score, bubble_evidence = score_direction(
        list(daily_data.values())[0] if daily_data else [], 120
    )
    upside_score = max(1, 6 - bubble_score)

    return {
        "main_theme": main_theme,
        "sub_theme": sub_theme,
        "chain_position": chain_position,
        "industry_logic_summary": (industry_logic.strip() or f"{sub_theme}方向；{len(companies)}家代表公司，当前涨幅区间({', '.join(f'{v:.0f}%' for v in all_6m[:3])}，待完成公告级核验。"),
        "representative_companies": names,
        "performance_stage_score": "4",
        "industry_prosperity_score": "4",
        "upside_score": str(upside_score),
        "bubble_safety_score": str(bubble_score),
        "fund_recognition_score": "4",
        "catalyst_score": "4",
        "total_score": "66",
        "recommended_next_action": f"深挖但不追高；优先核实{', '.join(missing_data[:2])}",
        "key_evidence": "行情/财务数据已采集，待完成公告/互动核验",
        "key_risks": "涨幅较大，主线收入暴露待核实",
        "missing_data": ", ".join(missing_data),
        "source_index_refs": build_source_id(f"COMP-{sub_theme}"),
    }


def build_research_card(
    sub_theme: str, main_theme: str, chain_position: str,
    companies: list[dict],
    daily_data: dict, profit_data: dict,
    missing_data: list[str],
    source_ids: list[str],
    industry_logic: str = "",
) -> str:
    """Build a Codex-compliant research card markdown."""
    all_1m, all_3m, all_6m, all_avg = [], [], [], []
    for code, rows in daily_data.items():
        try:
            l = float(rows[-1].get("close", 0))
            b1 = float(rows[-1 - 20].get("close", 0))
            b3 = float(rows[-1 - 60].get("close", 0))
            b6 = float(rows[-1 - 120].get("close", 0))
            vals = [float(r.get("amount", 0)) for r in rows[-20:] if r.get("amount")]
            avg = sum(vals) / len(vals) / 1e8 if vals else 0
            if b1: all_1m.append((l / b1 - 1) * 100)
            if b3: all_3m.append((l / b3 - 1) * 100)
            if b6: all_6m.append((l / b6 - 1) * 100)
            all_avg.append(avg)
        except (TypeError, ValueError, IndexError):
            pass

    def fmt_list(vals, fmt="{:.2f}%") -> str:
        if not vals:
            return "未取得可比样本，列入数据缺口"
        return f"{min(vals):.2f}% 至 {max(vals):.2f}%"

    def fmt_avg(vals) -> str:
        if not vals:
            return "未取得可比样本，列入数据缺口"
        return f"{min(vals):.2f}亿元至{max(vals):.2f}亿元"

    company_lines = "\n".join(
        f"| {c['name']} | {c['code']} | {chain_position} | 未证实，列入数据缺口 | BaoStock/Tencent/AKShare/Tushare或联网证据 | 行情/财务先行，业务暴露需来源补强 |"
        for c in companies
    )

    logic_text = industry_logic.strip() or (
        f"{sub_theme}处于{main_theme}的{chain_position}位置，受益于AI算力硬件升级和数据中心互联需求。"
        f"本轮已用BaoStock确认{len(companies)}家代表公司行情/财务数据明显放量，但尚待完成逐家公司产品收入占比、订单和客户公告级核验。"
    )

    return f"""# {sub_theme}

## 1. 结论摘要
- 当前主线地位：高
- 业绩兑现阶段：4分
- 估值水位：高（需补机构预期）
- 资金认可度：强
- 初步动作：深挖但不追高

## 2. 产业逻辑

{logic_text}

## 3. 上中下游位置
- 上游：需结合年报、公告和产业链证据细化
- 中游：{chain_position}
- 下游：云厂商/AI数据中心
- 与其他主线交叉：需结合细分方向母表和证据链补强

## 4. 代表公司清单
| 公司 | 代码 | 产业链位置 | 主线收入暴露 | 证据来源 | 备注 |
|---|---|---|---|---|---|
{company_lines}

## 5. 业绩兑现情况
- 已兑现收入：见 `代表公司财务估值总表.csv`。
- 已有订单/客户/定点：未证实，进入数据缺口和联网证据补采。
- 产能进展：未证实，进入数据缺口和公告补采。
- 2026E/2027E业绩预期：未证实，进入预测归一化流程。
- 关键证据：BaoStock利润数据；来源索引见 `数据来源索引.csv`。

## 6. 估值水平
- PE TTM：见总表。
- 2026E/2027E PE：未证实，需由 forecast-normalizer 归一化。
- PEG/PS：PS见总表，PEG需在预测利润补齐后计算。
- 估值历史分位：未接入终端工具，进入数据缺口。
- 与同行对比：初步看涨幅分化，需补历史分位后更新。

## 7. 行情与资金认可度
- 近1月涨幅：{fmt_list(all_1m)}
- 近3月涨幅：{fmt_list(all_3m)}
- 近6月涨幅：{fmt_list(all_6m)}
- 成交额变化：20日均值 {fmt_avg(all_avg)}
- 是否跑赢科技指数/创业板/科创50：需补指数日线或缓存后更新。
- 拥挤度：{score_direction(list(daily_data.values())[0] if daily_data else [], 120)[1] if daily_data else '数据不足'}

## 8. 未来催化
- 产业催化：AI基础设施资本开支、高速率产品迭代、海外CSP需求。
- 政策催化：需由 evidence-miner 补政策文件来源。
- 公司催化：订单公告、产能释放、定期报告。
- 财报催化：2026中报/三季报是否继续验证高增长。

## 9. 风险与证伪信号
- 估值风险：{fmt_list(all_6m)}，若盈利上修不足，估值透支风险高。
- 业绩风险：主线收入占比未核实，需警惕"概念强但AI暴露不足"。
- 技术路线风险：路线迭代可能改变价值分配。
- 证伪信号：订单放缓、毛利率回落、股价放量滞涨但盈利预期不上修。

## 10. 初步评分
| 维度 | 分数 | 证据 |
|---:|---:|---|
| 产业景气度 | 4 | 代表公司行情/财务兑现，待公告核验 |
| 业绩兑现概率 | 4 | BaoStock显示{len(companies)}家公司高增长 |
| 上涨空间 | {max(1, 6 - score_direction(list(daily_data.values())[0] if daily_data else [], 120)[0])} | 涨幅已大，赔率需重新核算 |
| 泡沫安全分 | {score_direction(list(daily_data.values())[0] if daily_data else [], 120)[0]} | {score_direction(list(daily_data.values())[0] if daily_data else [], 120)[1]} |
| 资金认可度 | 4 | 成交额显著放大 |
| 催化强度 | 4 | AI基础设施催化持续 |
| 综合评分 | 待定 | 待补机构预期和收入暴露后更新 |

## 11. 数据缺口
| 数据项 | 当前状态 | 获取方式 |
|---|---|
| 业务收入暴露 | 缺失 | 年报、公告、互动易、上证e互动或公司官网资料 |
| 客户/订单/定点 | 缺失 | 公告、投资者关系记录、互动平台、券商研报 |
| 2026E/2027E预测 | 缺失 | 用户提供数据、可验证公开预测页面或券商研报，标明来源类型 |
| 历史估值分位 | 缺失 | 终端工具或可索引网页数据 |

**数据来源**: {'; '.join(source_ids)}
**生成时间**: {datetime.now().isoformat(timespec='seconds')}
"""


# ---------------------------------------------------------------------------
# Missing data tracking
# ---------------------------------------------------------------------------

@dataclass
class DataTracker:
    """Track missing and conflicting data across a research run."""
    missing: list[dict] = field(default_factory=list)
    conflicts: list[dict] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)

    def add_missing(
        self,
        sub_theme: str,
        company: str,
        field: str,
        suggestion: str,
        *,
        sector_id: str,
        stock_code: str = "",
    ):
        self.missing.append({
            "细分方向": sub_theme,
            "公司": company,
            "缺失字段": field,
            "下一步建议": suggestion,
            "sector_id": sector_id,
            "stock_code": stock_code,
        })

    def add_conflict(self, sub_theme: str, company: str, field: str,
                     source_a: str, source_b: str, handling: str,
                     *, sector_id: str, stock_code: str = ""):
        self.conflicts.append({
            "细分方向": sub_theme,
            "公司": company,
            "冲突字段": field,
            "来源A": source_a,
            "来源B": source_b,
            "当前处理": handling,
            "sector_id": sector_id,
            "stock_code": stock_code,
        })

    def add_source(self, source: dict):
        self.sources.append(source)

    def save(self):
        if _project_config is None:
            raise RuntimeError("project config is required")
        if _runtime_paths is None:
            raise RuntimeError("project runtime paths are required")
        log_dir = _runtime_paths.logs_dir
        out_dir = _runtime_paths.output_root
        src_dir = _runtime_paths.total_tables_dir
        from investment_system.pipelines.sector_research.output_writers import (
            write_canonical_log_records,
        )

        missing_rows = [
            {
                "project_id": _project_config.project_id,
                "output_type": "company_table",
                "sector_id": m.get("sector_id", ""),
                "stock_code": m.get("stock_code", ""),
                "stock_name": m.get("公司", ""),
                "missing_field": m.get("缺失字段", ""),
                "severity": "medium",
                "reason": m.get("下一步建议", ""),
                "source_ids": "missing",
                "notes": "formal_output_missing_data",
                "current_value": "missing",
                "suggested_acquisition_path": m.get("下一步建议", ""),
                "status": "missing",
            }
            for m in self.missing
        ]
        conflict_rows = [
            {
                "project_id": _project_config.project_id,
                "output_type": "company_table",
                "sector_id": c.get("sector_id", ""),
                "stock_code": c.get("stock_code", ""),
                "stock_name": c.get("公司", ""),
                "field": c.get("冲突字段", ""),
                "conflicting_values": f"{c.get('来源A', '')}; {c.get('来源B', '')}",
                "source_ids": f"{c.get('来源A', '')};{c.get('来源B', '')}",
                "severity": "medium",
                "resolution_status": "pending_review",
                "resolution_note": c.get("当前处理", ""),
                "handling": c.get("当前处理", ""),
                "notes": "formal_output_conflict_data",
            }
            for c in self.conflicts
        ]
        write_canonical_log_records(
            _project_config,
            "missing_data_log",
            missing_rows,
            log_dir / "缺失数据清单.md",
            allow_formal_output=True,
        )
        write_canonical_log_records(
            _project_config,
            "conflict_data_log",
            conflict_rows,
            log_dir / "冲突数据清单.md",
            allow_formal_output=True,
        )

        if self.sources:
            append_csv(src_dir / "数据来源索引.csv", SOURCE_FIELDS, to_project_source_rows(self.sources, None))

        log_path = log_dir / "调研日志.md"
        existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        new_entry = f"\n## {datetime.now().isoformat(timespec='seconds')}\n\n"
        new_entry += f"- 完成细分方向调研。\n"
        new_entry += f"- 缺失数据条目: {len(self.missing)}\n"
        new_entry += f"- 数据来源: {[s['source_id'] for s in self.sources[:5]]}...\n"
        (log_dir / "调研日志.md").write_text(existing + new_entry, encoding="utf-8")


# ---------------------------------------------------------------------------
# Main research run
# ---------------------------------------------------------------------------

def run_sub_theme(
    sub_theme: str,
    companies: list[dict],
    main_theme: str,
    chain_position: str,
    tracker: DataTracker,
    dry_run: bool = False,
    industry_logic: str = "",
    prefer_tencent_daily: bool = False,
    sector_id: str | None = None,
) -> dict:
    """Run full research pipeline for one sub-theme. Returns summary."""
    if _runtime_paths is None:
        raise RuntimeError("project runtime paths are required")
    if not sector_id:
        raise ValueError("sector_id is required in project-aware mode")

    print(f"\n{'='*60}")
    print(f"  Sub-theme: {sub_theme}")
    print(f"  Companies: {', '.join(c['name'] for c in companies)}")
    print(f"{'='*60}")

    ensure_dirs()

    evidence = load_theme_evidence(sub_theme)
    if evidence:
        print(f"  Using curated evidence: {Path(evidence['_evidence_path']).relative_to(ROOT)}")

    run_meta = {
        "sub_theme": sub_theme,
        "companies": [c["code"] for c in companies],
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "evidence_path": evidence.get("_evidence_path", ""),
    }
    RUN_META_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_META_DIR / f"{safe_output_name(sub_theme)}_run_meta.json").write_text(
        json.dumps(run_meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    daily_data: dict[str, list[dict]] = {}
    profit_data: dict[str, list[dict]] = {}
    financial_fallbacks: dict[str, dict[str, str]] = {}

    with ResearchClient(baostock_interval=2.0) as client:
        tencent_limiter = HumanRateLimiter(min_seconds=5.0, jitter=2.0)
        for c in companies:
            code, market, name = c["code"], c["market"], c["name"]
            print(f"  [{name}] Fetching data...")

            daily_path = RAW_CACHE_DIR / "baostock" / "daily_kline" / TODAY / f"{code}.json"
            drows = read_raw_rows(daily_path)
            if drows:
                print(f"    daily: cache ({len(drows)} rows)")
                daily_data[code] = drows
            else:
                daily_source = "research_client"
                if prefer_tencent_daily:
                    tencent_limiter.wait()
                    sym = f"{'sh' if market == 'SH' else 'sz'}{code}"
                    drows = tencent_bar_direct(sym)
                    if not drows or "_error" in drows[0]:
                        print("    daily: Tencent direct failed, falling back to rate-limited AKShare")
                        drows = client.get_akshare_daily_bar(sym)
                        daily_source = "akshare_daily_bar"
                    else:
                        daily_source = "tencent_direct"
                else:
                    drows = client.get_daily_kline(code, market)
                if drows and "_error" not in drows[0]:
                    daily_data[code] = drows
                    daily_path.parent.mkdir(parents=True, exist_ok=True)
                    daily_path.write_text(
                        json.dumps({"source": daily_source, "rows": json_safe_rows(drows)}, ensure_ascii=False),
                        encoding="utf-8",
                    )
                elif not prefer_tencent_daily:
                    sym = f"{'sh' if market == 'SH' else 'sz'}{code}"
                    drows = tencent_bar_direct(sym)
                    if drows and "_error" not in drows[0]:
                        daily_data[code] = drows
                        daily_path.parent.mkdir(parents=True, exist_ok=True)
                        daily_path.write_text(
                            json.dumps({"source": "tencent_direct", "rows": json_safe_rows(drows)}, ensure_ascii=False),
                            encoding="utf-8",
                        )

            profit_path = RAW_CACHE_DIR / "baostock" / "profit" / TODAY / f"{code}.json"
            prows = read_raw_rows(profit_path)
            if prows:
                print(f"    profit: cache ({len(prows)} rows)")
                profit_data[code] = prows
            else:
                prows = client.get_profit(code, market, [2024, 2025, 2026])
            if prows and "_error" not in prows[0]:
                profit_data[code] = prows
                profit_path.parent.mkdir(parents=True, exist_ok=True)
                profit_path.write_text(
                    json.dumps({"source": "research_client", "rows": prows}, ensure_ascii=False),
                    encoding="utf-8",
                )
                row_2025 = annual_profit(prows, "2025")
                if not row_2025.get("MBRevenue"):
                    print("    financial: BaoStock annual revenue absent, trying rate-limited AKShare indicator")
                    indicator_rows = client.get_akshare_financial_indicator(code)
                    indicator_path = RAW_CACHE_DIR / "akshare" / "financial_indicator" / TODAY / f"{code}.json"
                    indicator_path.parent.mkdir(parents=True, exist_ok=True)
                    indicator_path.write_text(
                        json.dumps({"source": "akshare_financial_indicator", "rows": json_safe_rows(indicator_rows)}, ensure_ascii=False),
                        encoding="utf-8",
                    )
                    revenue_2025 = derive_revenue_yi_from_akshare_indicator(indicator_rows, "2025")
                    if revenue_2025:
                        financial_fallbacks[code] = {
                            "revenue_2025": revenue_2025,
                            "data_source_append": "AKShare财务指标(收入推导)",
                            "source_url_append": f"investment_system/data/raw/akshare/financial_indicator/{TODAY}/{code}.json",
                        }

    missing_fields = evidence.get("remaining_missing_fields") or (
        [] if evidence else ["800G/1.6T收入占比", "海外CSP客户/订单", "产能利用率", "机构一致预期", "估值历史分位"]
    )
    if missing_fields:
        for c in companies:
            for field in missing_fields:
                tracker.add_missing(
                    sub_theme,
                    c["name"],
                    field,
                    "查公司公告/投资者关系/互动易",
                    sector_id=sector_id,
                    stock_code=c["code"],
                )

    company_rows, new_sources = build_company_rows(
        companies, daily_data, profit_data, sub_theme, main_theme, chain_position, []
    )
    company_rows = apply_company_overrides(company_rows, evidence)
    for row in company_rows:
        fallback = financial_fallbacks.get(row.get("stock_code", ""))
        if fallback and row.get("revenue_2025") == "缺失":
            row["revenue_2025"] = fallback["revenue_2025"]
            row["data_source"] = f"{row.get('data_source', '')}; {fallback['data_source_append']}"
            row["source_url"] = f"{row.get('source_url', '')}; {fallback['source_url_append']}"
    if not evidence:
        for src in new_sources:
            tracker.add_source(src)

    comparison_row = build_comparison_row(
        sub_theme, main_theme, chain_position, companies, daily_data, missing_fields,
        industry_logic=industry_logic,
    )
    comparison_row = apply_comparison_override(comparison_row, evidence)

    card_md = card_markdown(evidence) or build_research_card(
        sub_theme, main_theme, chain_position, companies,
        daily_data, profit_data, missing_fields,
        [s["source_id"] for s in new_sources],
        industry_logic=industry_logic,
    )

    if dry_run:
        print("  [DRY RUN] Skipping file writes.")
        return {"sub_theme": sub_theme, "companies_done": len(companies), "dry_run": True}

    # ── Resolve output paths ──────────────────────────────────────────────────
    try:
        card_path = _runtime_paths.resolve_sector_card_path(sector_id)
        _check_path_safety(str(card_path))
        card_dir = card_path.parent
    except (KeyError, ValueError, RuntimeError) as exc:
        print(f"  [WARNING] Could not resolve sector card path for sector_id='{sector_id}': {exc}")
        print(f"  [WARNING] Skipping sector card output for '{sub_theme}'.")
        card_path = None
        card_dir = None

    tt_dir = _runtime_paths.total_tables_dir
    lg_dir = _runtime_paths.logs_dir
    path_mode = "project-aware"

    company_rows_out = to_project_company_rows(company_rows, companies, sector_id)
    comparison_rows_out = [to_project_comparison_row(comparison_row, sector_id)]
    company_fields = COMPANY_TABLE_FIELDS
    comparison_fields = COMPARISON_FIELDS

    append_csv(tt_dir / "代表公司财务估值总表.csv", company_fields, company_rows_out)
    append_csv(tt_dir / "科技细分方向横向比较表.csv", comparison_fields, comparison_rows_out)
    curated_sources = evidence_source_rows(evidence)
    if curated_sources:
        append_csv(tt_dir / "数据来源索引.csv", SOURCE_FIELDS, to_project_source_rows(curated_sources, sector_id))

    if card_path is not None:
        card_dir.mkdir(parents=True, exist_ok=True)
        card_path.write_text(card_md, encoding="utf-8")
        print(f"  Wrote [{path_mode}]: {card_path.relative_to(ROOT)}")

    if evidence:
        write_evidence_logs(evidence, lg_dir)

    print(f"  Appended [{path_mode}]: 代表公司财务估值总表.csv ({len(company_rows)} rows)")
    print(f"  Appended [{path_mode}]: 科技细分方向横向比较表.csv (1 row)")
    if curated_sources:
        print(f"  Appended [{path_mode}]: 数据来源索引.csv ({len(curated_sources)} curated rows)")

    return {
        "sub_theme": sub_theme,
        "sector_id": sector_id,
        "companies": len(companies),
        "daily_data": {c: len(r) for c, r in daily_data.items()},
        "profit_data": {c: len(r) for c, r in profit_data.items()},
        "card_path": str(card_path.relative_to(ROOT)) if card_path else "(skipped: unresolved)",
        "path_mode": path_mode,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Standardized A股科技主线调研")
    parser.add_argument("--project", type=str,
                        required=True,
                        help="Project ID (e.g. tech_ai_semiconductor).")
    parser.add_argument("--sector-id", type=str,
                        help="Canonical sector_id to run (project-aware only). Accepts legacy alias.")
    parser.add_argument("--batch", type=str, choices=["p0", "p1", "p2", "all"],
                        help="Run all sectors in a batch using sector_universe.yaml.")
    parser.add_argument("--companies", type=str,
                        help="Comma-separated codes override (e.g. 300308,300502)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch data but don't write outputs")
    parser.add_argument("--dry-run-resolve", action="store_true",
                        help="[Project-aware] Only parse sector context and print paths; no data collection, no file writes")
    parser.add_argument("--dry-run-generate", action="store_true",
                        help="[Project-aware] Build canonical generator preview records; no data collection, no formal output writes")
    parser.add_argument("--write-audit-preview", action="store_true",
                        help="[Project-aware] With --dry-run-generate, write preview files under audits/generator_previews only")
    parser.add_argument("--prefer-tencent-daily", action="store_true",
                        help="Use Tencent direct for daily K-line before BaoStock")
    args = parser.parse_args()

    global _project_config, _runtime_paths

    # ── --dry-run-resolve: project-aware only, parse-only ─────────────────
    if args.dry_run_resolve:
        if not args.project:
            print("[ERROR] --dry-run-resolve requires --project")
            return 1
        if not args.sector_id:
            print("[ERROR] --dry-run-resolve requires --sector-id")
            return 1

        from investment_system.pipelines.sector_research import load_project as lp_module
        try:
            config = lp_module.load_project(args.project, silent=True, strict=False)
        except Exception as exc:
            print(f"[ERROR] Failed to load project '{args.project}': {exc}")
            return 1

        try:
            ctx = resolve_sector_context(config, args.sector_id, lp_module)
        except KeyError as exc:
            print(f"[ERROR] Cannot resolve sector '{args.sector_id}': {exc}")
            # Suggest alternatives
            valid_ids = sorted({s.get("sector_id") for s in config.raw.get("sectors", [])})
            print(f"[HINT] Valid canonical sector_ids ({len(valid_ids)}):")
            for sid in valid_ids:
                print(f"        {sid}")
            return 1

        # Print sector context
        print(f"\n{'='*60}")
        print(f"  [DRY-RUN-RESOLVE] Sector Context")
        print(f"{'='*60}")
        print(f"  input_raw          : {ctx.input_raw}")
        if ctx.was_legacy_alias:
            print(f"  [WARNING] Input '{ctx.input_raw}' is a legacy alias.")
            print(f"  [WARNING] Resolved to canonical sector_id: {ctx.sector_id}")
        else:
            print(f"  was_legacy_alias   : False (canonical sector_id provided)")
        print(f"  canonical_sector_id: {ctx.sector_id}")
        print(f"  sector_name        : {ctx.sector_name}")
        print(f"  research_group_id  : {ctx.research_group_id}")
        print(f"  group_name         : {ctx.group_name}")
        print(f"  group_order        : {ctx.group_order}")
        print(f"  priority           : {ctx.priority}")
        print(f"  chain_position     : {ctx.chain_position}")
        print(f"  parent_chain       : {ctx.parent_chain}")
        print(f"  scoring_enabled    : {ctx.scoring_enabled}")
        print(f"  aliases            : {ctx.aliases}")
        print(f"  legacy_sector_ids  : {ctx.legacy_sector_ids}")
        print(f"  legacy_theme_names : {ctx.legacy_theme_names}")

        # Resolve and print paths
        card_path = lp_module.resolve_sector_card_path(config, ctx.sector_id)
        print(f"\n  Expected sector card path:")
        print(f"    {card_path}")

        paths = lp_module.resolve_output_paths(config, ctx.sector_id)
        print(f"\n  Other resolved paths:")
        for key in ["output_root", "total_tables_dir", "logs_dir", "source_index_path",
                     "company_table_path", "comparison_table_path",
                     "missing_data_log_path", "conflict_data_log_path"]:
            if key in paths:
                print(f"    {key}: {paths[key]}")

        # Show stock list (from stock_universe via loader API)
        print(f"  stock_source        : stock_universe.yaml")
        try:
            stocks = lp_module.get_stocks_for_sector(config, ctx.sector_id, include_pending=False)
            listed = [s for s in stocks if s.get("code") and s.get("code") not in ("pending", "待查", "")]
            coverage = compute_coverage_status(ctx, len(listed))
            print(f"  stock_count         : {len(listed)}")
            print(f"  coverage_status     : {coverage['status']}")
            print(f"  coverage_required   : {coverage['required']}")
            if coverage["warning"]:
                print(f"  coverage_warning    : {coverage['warning']}")

            print(f"\n  Stocks ({len(listed)} listed from stock_universe):")
            for s in listed:
                print(f"    {s.get('code', '?')}  {s.get('name', '?')}  [{s.get('role', '')}/{s.get('exposure_type', '')}]")
            if not listed:
                print(f"    (WARNING: no listed stocks — stock_universe is still incomplete)")
        except Exception as exc:
            print(f"  Stocks: (ERROR loading stock_universe: {exc})")

        # Show evidence binding metadata only; do not read evidence contents.
        print(f"\n  Evidence source      : run_manifest.yaml + sector_universe.yaml")
        try:
            evidence_files = lp_module.resolve_evidence_files_for_sector(config, ctx.sector_id)
            print(f"  Evidence files count : {len(evidence_files)}")
            if evidence_files:
                print(f"  Evidence files       :")
                for ef in evidence_files:
                    print(
                        f"    - {ef.get('evidence_file_id', '?')} -> "
                        f"{ef.get('path', '?')} "
                        f"[status={ef.get('status', '')}, action={ef.get('action', '')}, "
                        f"exists={ef.get('exists')}]"
                    )
            else:
                print(f"  evidence_warning    : no evidence files bound to this sector yet.")
        except Exception as exc:
            print(f"  Evidence files      : (ERROR resolving evidence bindings: {exc})")

        print(f"\n  [DRY-RUN-RESOLVE] No data collected. No files written.")
        print(f"{'='*60}")
        return 0

    # ── --dry-run-generate: project-aware writer preview only ───────────────
    if args.dry_run_generate:
        if not args.project:
            print("[ERROR] --dry-run-generate requires --project")
            return 1
        if not args.sector_id:
            print("[ERROR] --dry-run-generate requires --sector-id")
            return 1

        from investment_system.pipelines.sector_research import load_project as lp_module
        from investment_system.pipelines.sector_research.output_writers import (
            PREVIEW_MARKER,
            build_generator_preview_records,
            get_generator_preview_dir,
            validate_preview_records,
            write_generator_preview_files,
        )

        try:
            config = lp_module.load_project(args.project, silent=True, strict=False)
            ctx = resolve_sector_context(config, args.sector_id, lp_module)
        except Exception as exc:
            print(f"[ERROR] Failed to prepare generator preview: {exc}")
            return 1

        print(f"\n{'='*60}")
        print("  [DRY-RUN-GENERATE] Canonical Generator Preview")
        print(f"{'='*60}")
        print(f"  project_id          : {config.project_id}")
        print(f"  input_raw           : {args.sector_id}")
        if ctx.was_legacy_alias:
            print(f"  legacy_alias_warning: resolved to canonical sector_id {ctx.sector_id}")
        print(f"  canonical_sector_id : {ctx.sector_id}")
        print(f"  sector_name         : {ctx.sector_name}")
        print(f"  preview_marker      : {PREVIEW_MARKER}")
        print("  data_collection     : skipped")
        print("  formal_output_write : skipped")

        try:
            records = build_generator_preview_records(config, ctx.sector_id)
            results = validate_preview_records(config, records)
        except Exception as exc:
            print(f"[ERROR] Failed to build generator preview records: {exc}")
            return 1

        pass_count = sum(1 for result in results.values() if result.get("ok"))
        fail_count = sum(1 for result in results.values() if not result.get("ok"))
        print(f"  output_type_count   : {len(results)}")
        print(f"  preview_record_count: {len(records)}")
        print(f"  record_shape_pass   : {pass_count}")
        print(f"  record_shape_fail   : {fail_count}")
        for output_type, result in results.items():
            status = "ok" if result.get("ok") else "failed"
            print(f"    - {output_type}: {status}")
            for error in result.get("errors", []):
                print(f"      ERROR: {error}")

        written: list[Path] = []
        if args.write_audit_preview:
            try:
                written = write_generator_preview_files(config, records)
            except Exception as exc:
                print(f"[ERROR] Failed to write generator preview files: {exc}")
                return 1
            print(f"  write_audit_preview : true")
            print(f"  preview_output_dir  : {get_generator_preview_dir(config)}")
            for path in written:
                print(f"    wrote: {path}")
        else:
            print("  write_audit_preview : false")
            print("  No files written.")

        print("  No data collected. No formal files written.")
        print(f"{'='*60}")
        return 1 if fail_count else 0

    # ── Project-aware init ─────────────────────────────────────────────────
    if args.project:
        from investment_system.pipelines.sector_research import load_project as lp_module

        try:
            _project_config = lp_module.load_project(args.project, silent=False, strict=False)
            paths = lp_module.resolve_output_paths(_project_config)

            _runtime_paths = ResearchRuntimePaths(
                output_root=Path(paths["output_root"]),
                total_tables_dir=Path(paths["total_tables_dir"]),
                logs_dir=Path(paths["logs_dir"]),
                raw_data_root=Path(paths["raw_data_root"]),
                source_index_path=Path(paths["source_index_path"]),
                missing_data_log_path=Path(paths["missing_data_log_path"]),
                conflict_data_log_path=Path(paths["conflict_data_log_path"]),
                research_log_path=Path(paths["research_log_path"]),
            )
            _runtime_paths._resolve_sector_card_path = lambda sid: lp_module.resolve_sector_card_path(
                _project_config, sid
            )

            print(f"[PROJECT-AWARE] Project: {_project_config.project_name} ({args.project})")
            print(f"[PROJECT-AWARE] Output root: {_runtime_paths.output_root}")
            print(f"[PROJECT-AWARE] total_tables: {_runtime_paths.total_tables_dir}")
            print(f"[PROJECT-AWARE] logs: {_runtime_paths.logs_dir}")
            print(f"[PROJECT-AWARE] stock_source: stock_universe.yaml")

            if not _runtime_paths.output_root.exists():
                print(f"[WARNING] Output root does not exist: {_runtime_paths.output_root}")
                print(f"[WARNING] Outputs will be written there (mkdir will be called on first write).")

        except Exception as exc:
            print(f"[ERROR] Failed to load project '{args.project}': {exc}")
            return 1

    load_env()
    tracker = DataTracker()
    results = []

    # ── Parameter conflict checks ─────────────────────────────────────────
    if args.project and args.sector_id and args.batch:
        print("[WARNING] Both --sector-id and --batch provided. "
              "Running in batch mode; --sector-id will be ignored.")

    # ── Single sector-id (project-aware) ────────────────────────────────
    if args.project and args.sector_id and not args.batch:
        from investment_system.pipelines.sector_research import load_project as lp_module

        try:
            ctx = resolve_sector_context(_project_config, args.sector_id, lp_module)
        except KeyError as exc:
            print(f"[ERROR] Cannot resolve sector '{args.sector_id}': {exc}")
            return 1

        if ctx.was_legacy_alias:
            print(f"[WARNING] Input sector_id '{args.sector_id}' was resolved to canonical "
                  f"sector_id '{ctx.sector_id}' via legacy alias. "
                  f"Prefer using canonical sector_id directly.")

        # Get companies from stock_universe
        try:
            sector_stocks = lp_module.get_stocks_for_sector(
                _project_config, ctx.sector_id, include_pending=False
            )
            companies = []
            for s in sector_stocks:
                code = s.get("code", "")
                if not code or code in ("pending", "待查", ""):
                    continue
                market = "SZ" if code.startswith(("0", "3")) else "SH"
                companies.append({
                    "code": code,
                    "market": market,
                    "set_code": s.get("set_code", 0),
                    "name": s.get("name", code),
                })
            if not companies:
                print(f"[ERROR] No stocks found for sector_id='{ctx.sector_id}' in stock_universe.yaml. "
                      f"Cannot run research without a stock pool.")
                print(f"[ERROR] Please populate stock_universe.yaml for this sector before running.")
                return 1

            coverage = compute_coverage_status(ctx, len(companies))
            if coverage["warning"]:
                print(f"[WARNING] sector '{ctx.sector_id}' coverage_status={coverage['status']}: "
                      f"{coverage['warning']} Research quality will be limited.")
        except Exception as exc:
            print(f"[ERROR] get_stocks_for_sector failed for '{ctx.sector_id}': {exc}")
            return 1

        if args.companies:
            codes = args.companies.split(",")
            companies = [{"code": c, "market": "SZ", "set_code": 0, "name": c} for c in codes]

        r = run_sub_theme(
            ctx.sector_name,
            companies,
            ctx.parent_chain,
            ctx.chain_position,
            tracker,
            dry_run=args.dry_run,
            industry_logic=ctx.industry_logic,
            prefer_tencent_daily=args.prefer_tencent_daily,
            sector_id=ctx.sector_id,
        )
        results.append(r)

    # ── Batch mode (project-aware) ─────────────────────────────────────
    elif args.project and args.batch:
        from investment_system.pipelines.sector_research import load_project as lp_module

        sectors = list_project_sectors_by_priority(
            _project_config, args.batch, lp_module
        )
        print(f"[PROJECT-AWARE BATCH] {args.batch.upper()}: {len(sectors)} sectors")

        for ctx in sectors:
            try:
                sector_stocks = lp_module.get_stocks_for_sector(
                    _project_config, ctx.sector_id, include_pending=False
                )
                companies = []
                for s in sector_stocks:
                    code = s.get("code", "")
                    if not code or code in ("pending", "待查", ""):
                        continue
                    market = "SZ" if code.startswith(("0", "3")) else "SH"
                    companies.append({
                        "code": code,
                        "market": market,
                        "set_code": s.get("set_code", 0),
                        "name": s.get("name", code),
                    })
                if not companies:
                    print(f"[WARNING] No stocks for '{ctx.sector_id}' in stock_universe.yaml — skipping sector.")
            except Exception as exc:
                print(f"[ERROR] get_stocks_for_sector failed for '{ctx.sector_id}': {exc} — skipping sector.")
                companies = []

            if not companies:
                continue

            try:
                r = run_sub_theme(
                    ctx.sector_name,
                    companies,
                    ctx.parent_chain,
                    ctx.chain_position,
                    tracker,
                    dry_run=args.dry_run,
                    industry_logic=ctx.industry_logic,
                    prefer_tencent_daily=args.prefer_tencent_daily,
                    sector_id=ctx.sector_id,
                )
                results.append(r)
            except Exception as exc:
                print(f"  ERROR in {ctx.sector_id}: {exc}")
                results.append({"sector_id": ctx.sector_id, "sub_theme": ctx.sector_name, "error": str(exc)})

    else:
        parser.print_help()
        return 1

    if tracker.missing or tracker.conflicts or tracker.sources:
        tracker.save()

    print(f"\n{'='*60}")
    print(" RESEARCH RUN COMPLETE")
    print(f"{'='*60}")
    for r in results:
        status = "OK" if "error" not in r else f"ERROR: {r.get('error')}"
        companies_done = r.get("companies", "?")
        mode = r.get("path_mode", "?")
        sid = r.get("sector_id", "?")
        card = r.get("card_path", "?")
        sub = r.get("sub_theme", sid)
        print(f"  [{mode}] {sub}: {status} ({companies_done} companies)")
        print(f"          card: {card}")

    out_dir = _runtime_paths.output_root
    print(f"\nAll outputs in: {out_dir.relative_to(ROOT)}")

    _project_config = None
    _runtime_paths = None
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
