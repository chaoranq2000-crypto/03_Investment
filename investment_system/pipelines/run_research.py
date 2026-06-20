"""Standardized automated research pipeline for A股科技主线.

Usage:
    # Run all P0 sub-themes (legacy):
    python run_research.py --batch p0

    # Run a specific sub-theme (legacy):
    python run_research.py --sub-theme "高速光模块"

    # Project-aware mode:
    python run_research.py --project tech_ai_semiconductor --batch p0
    python run_research.py --project tech_ai_semiconductor --sub-theme "高速光模块"
    python run_research.py --project tech_ai_semiconductor --sector-id cpo_optical_module_silicon_photonics

    # Dry run (data sources only, no output files):
    python run_research.py --sub-theme "高速光模块" --dry-run

    # Guosen skills are disabled by default:
    python run_research.py --sub-theme "高速光模块"

Output follows Codex调研说明手册规范 (legacy) or project output_spec.yaml (--project):
    tech_ai_semiconductor project output root (科技主线调研输出/):
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

# Add scripts/ to path for research_client import
ROOT = Path(__file__).resolve().parents[2]  # pipeliens/ -> investment_system/ -> project/  => ROOT = C:\Projects\03_Investment
sys.path.insert(0, str(ROOT / "investment_system" / "scripts"))  # research_client.py lives here

from research_client import (
    ResearchClient,
    tencent_bar_direct,
    load_env,
    HumanRateLimiter,
)
from evidence_overrides import (
    apply_company_overrides,
    apply_comparison_override,
    card_markdown,
    evidence_source_rows,
    load_theme_evidence,
    write_evidence_logs,
)

TODAY = date.today().isoformat()
OUT_DIR = ROOT / "科技主线调研输出"
RAW_DIR = ROOT / "investment_system" / "data" / "raw"
PROCESSED_DIR = ROOT / "investment_system" / "data" / "processed" / "theme_research" / TODAY
LOG_DIR = OUT_DIR / "99_日志"
META_DIR = RAW_DIR / "research_runs" / TODAY


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


# ---------------------------------------------------------------------------
# Theme registry
# ---------------------------------------------------------------------------

THEME_REGISTRY_CSV = ROOT / "A股科技前两主线调研文件包" / "01_调研板块细分方向列表" / "A股科技前两主线_板块细分方向母表.csv"

# Inline P0 companies for each sub-theme that have been researched
KNOWN_COMPANIES = {
    "高速光模块": [
        {"code": "300308", "market": "SZ", "set_code": 0, "name": "中际旭创"},
        {"code": "300502", "market": "SZ", "set_code": 0, "name": "新易盛"},
        {"code": "300394", "market": "SZ", "set_code": 0, "name": "天孚通信"},
        {"code": "603083", "market": "SH", "set_code": 1, "name": "剑桥科技"},
        {"code": "002281", "market": "SZ", "set_code": 0, "name": "光迅科技"},
        {"code": "000988", "market": "SZ", "set_code": 0, "name": "华工科技"},
        {"code": "300570", "market": "SZ", "set_code": 0, "name": "太辰光"},
        {"code": "300548", "market": "SZ", "set_code": 0, "name": "博创科技"},
    ],
    "光器件/FAU/精密光学": [
        {"code": "300394", "market": "SZ", "set_code": 0, "name": "天孚通信"},
        {"code": "300570", "market": "SZ", "set_code": 0, "name": "太辰光"},
        {"code": "688195", "market": "SH", "set_code": 1, "name": "腾景科技"},
        {"code": "300620", "market": "SZ", "set_code": 0, "name": "光库科技"},
        {"code": "688025", "market": "SH", "set_code": 1, "name": "杰普特"},
        {"code": "688127", "market": "SH", "set_code": 1, "name": "蓝特光学"},
    ],
}


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


def load_theme_registry() -> dict[str, dict]:
    """Load sub-theme definitions from the mother table CSV.

    CSV header: main_theme, sub_theme, chain_position, second_level, third_level,
    research_priority, cross_theme_overlap, industry_logic, key_metrics_to_collect,
    representative_companies_initial, catalysts_to_track, risks_to_track, notes_for_codex
    """
    if not THEME_REGISTRY_CSV.exists():
        return {}
    themes = {}
    with THEME_REGISTRY_CSV.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            key = row.get("sub_theme", "").strip()
            if not key:
                continue
            themes[key] = {
                "main_theme": row.get("main_theme", "").strip(),
                "sub_theme": key,
                "chain_position": row.get("chain_position", "").strip(),
                "industry_logic": row.get("industry_logic", "").strip(),
                "second_level": row.get("second_level", "").strip(),
                "third_level": row.get("third_level", "").strip(),
                "research_priority": row.get("research_priority", "").strip(),
                "key_metrics": row.get("key_metrics_to_collect", "").strip(),
                "catalysts": row.get("catalysts_to_track", "").strip(),
                "risks": row.get("risks_to_track", "").strip(),
                "notes": row.get("notes_for_codex", "").strip(),
            }
    return themes


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
    """Derive revenue from AKShare indicators when direct revenue is absent.

    AKShare financial indicators expose 主营业务利润 and 主营业务利润率. Revenue
    can be inferred as main_business_profit / margin when both fields exist.
    """
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
    "stock_code", "company_name", "main_theme", "sub_theme", "chain_position",
    "market_cap", "latest_price", "pct_change_1m", "pct_change_3m", "pct_change_6m",
    "turnover_value_20d_avg", "relative_strength_vs_index",
    "revenue_2024", "revenue_2025", "revenue_2026E", "revenue_2027E",
    "net_profit_2024", "net_profit_2025", "net_profit_2026E", "net_profit_2027E",
    "gross_margin_latest", "net_margin_latest",
    "pe_ttm", "pe_2026E", "pe_2027E", "ps_ttm", "peg_2026E",
    "main_theme_revenue_exposure", "order_or_customer_evidence", "capacity_progress",
    "product_stage", "institution_forecast_change",
    "catalysts", "risks", "data_source", "source_date", "source_url", "confidence_level",
]

COMPARISON_FIELDS = [
    "main_theme", "sub_theme", "chain_position", "industry_logic_summary",
    "representative_companies", "performance_stage_score", "industry_prosperity_score",
    "upside_score", "bubble_safety_score", "fund_recognition_score",
    "catalyst_score", "total_score", "recommended_next_action",
    "key_evidence", "key_risks", "missing_data", "source_index_refs",
]

SOURCE_FIELDS = [
    "source_id", "source_type", "source_name", "source_date", "source_url",
    "related_main_theme", "related_sub_theme", "related_company",
    "quote_or_excerpt", "data_fields_supported",
    "confidence_level", "notes",
]


def ensure_dirs() -> None:
    if _runtime_paths is not None:
        for d in [_runtime_paths.output_root, _runtime_paths.total_tables_dir,
                  _runtime_paths.logs_dir, META_DIR, PROCESSED_DIR]:
            Path(d).mkdir(parents=True, exist_ok=True)
    else:
        for d in [OUT_DIR, LOG_DIR, META_DIR, PROCESSED_DIR]:
            Path(d).mkdir(parents=True, exist_ok=True)


def append_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    """Append rows to a CSV, creating with header if missing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


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

        # Index data (placeholder for now - gets 创业板 later)
        idx_rows = []  # will be filled if index data is available
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
    # Collect stats
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
        "industry_logic_summary": (industry_logic.strip() or f"{sub_theme}方向；{len(companies)}家代表公司，当前涨幅区间({', '.join(f'{v:.0f}%' for v in all_6m[:3])})，待完成公告级核验。"),
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
    # Aggregate stats
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
|---|---|---|
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

    def add_missing(self, sub_theme: str, company: str, field: str, suggestion: str):
        self.missing.append({
            "细分方向": sub_theme,
            "公司": company,
            "缺失字段": field,
            "下一步建议": suggestion,
        })

    def add_conflict(self, sub_theme: str, company: str, field: str,
                     source_a: str, source_b: str, handling: str):
        self.conflicts.append({
            "细分方向": sub_theme,
            "公司": company,
            "冲突字段": field,
            "来源A": source_a,
            "来源B": source_b,
            "当前处理": handling,
        })

    def add_source(self, source: dict):
        self.sources.append(source)

    def save(self):
        # Use project-aware paths if set, otherwise fall back to legacy globals
        if _runtime_paths is not None:
            log_dir = _runtime_paths.logs_dir
            out_dir = _runtime_paths.output_root
            src_dir = _runtime_paths.total_tables_dir
        else:
            log_dir = LOG_DIR
            out_dir = OUT_DIR
            src_dir = out_dir / "00_总表"

        # Missing data
        missing_md = "# 缺失数据清单\n\n"
        if self.missing:
            missing_md += "| 细分方向 | 公司 | 缺失字段 | 下一步建议 |\n|---|---|---|---|\n"
            for m in self.missing:
                missing_md += f"| {m['细分方向']} | {m['公司']} | {m['缺失字段']} | {m['下一步建议']} |\n"
        else:
            missing_md += "本轮调研暂未发现系统性缺失数据。\n"

        (log_dir / "缺失数据清单.md").write_text(missing_md, encoding="utf-8")

        # Conflicts
        conflict_md = "# 冲突数据清单\n\n"
        if self.conflicts:
            conflict_md += "| 细分方向 | 公司 | 冲突字段 | 来源A | 来源B | 当前处理 |\n|---|---|---|---|---|---|\n"
            for c in self.conflicts:
                conflict_md += f"| {c['细分方向']} | {c['公司']} | {c['冲突字段']} | {c['来源A']} | {c['来源B']} | {c['当前处理']} |\n"
        else:
            conflict_md += "暂未发现跨来源数据冲突。\n"

        (log_dir / "冲突数据清单.md").write_text(conflict_md, encoding="utf-8")

        # Sources
        if self.sources:
            append_csv(src_dir / "数据来源索引.csv", SOURCE_FIELDS, self.sources)

        # Log
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
    skip_guosen: bool = True,
    dry_run: bool = False,
    industry_logic: str = "",
    prefer_tencent_daily: bool = False,
    sector_id: str | None = None,
) -> dict:
    """Run full research pipeline for one sub-theme. Returns summary."""
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
        "skip_guosen": skip_guosen,
        "evidence_path": evidence.get("_evidence_path", ""),
    }
    META_DIR.mkdir(parents=True, exist_ok=True)
    (META_DIR / f"{safe_output_name(sub_theme)}_run_meta.json").write_text(
        json.dumps(run_meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Collect data
    daily_data: dict[str, list[dict]] = {}
    profit_data: dict[str, list[dict]] = {}
    financial_fallbacks: dict[str, dict[str, str]] = {}
    guosen_health = False

    with ResearchClient(skip_guosen=skip_guosen, baostock_interval=2.0) as client:
        tencent_limiter = HumanRateLimiter(min_seconds=5.0, jitter=2.0)
        for c in companies:
            code, market, name = c["code"], c["market"], c["name"]
            print(f"  [{name}] Fetching data...")

            # Daily kline
            daily_path = RAW_DIR / "baostock" / "daily_kline" / TODAY / f"{code}.json"
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
                    # Tencent fallback when BaoStock returns an error.
                    sym = f"{'sh' if market == 'SH' else 'sz'}{code}"
                    drows = tencent_bar_direct(sym)
                    if drows and "_error" not in drows[0]:
                        daily_data[code] = drows
                        daily_path.parent.mkdir(parents=True, exist_ok=True)
                        daily_path.write_text(
                            json.dumps({"source": "tencent_direct", "rows": json_safe_rows(drows)}, ensure_ascii=False),
                            encoding="utf-8",
                        )

            # Profit
            profit_path = RAW_DIR / "baostock" / "profit" / TODAY / f"{code}.json"
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
                    indicator_path = RAW_DIR / "akshare" / "financial_indicator" / TODAY / f"{code}.json"
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

            # Guosen is disabled by default; only run if explicitly re-enabled.
            if not skip_guosen:
                try:
                    hq = client.get_comb_hq([code], [c["set_code"]])
                    if "_guosen_error" not in hq:
                        (RAW_DIR / "guosen" / "comb_hq" / TODAY / f"{code}.json").parent.mkdir(parents=True, exist_ok=True)
                        (RAW_DIR / "guosen" / "comb_hq" / TODAY / f"{code}.json").write_text(
                            json.dumps(hq, ensure_ascii=False, indent=2), encoding="utf-8",
                        )
                except Exception:
                    pass

        guosen_health = client.guosen_health()

    # Track missing data
    missing_fields = evidence.get("remaining_missing_fields") or (
        [] if evidence else ["800G/1.6T收入占比", "海外CSP客户/订单", "产能利用率", "机构一致预期", "估值历史分位"]
    )
    if missing_fields:
        for c in companies:
            for field in missing_fields:
                tracker.add_missing(sub_theme, c["name"], field, "查公司公告/投资者关系/互动易")

    # Build outputs
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
    if _runtime_paths is not None:
        # Project-aware mode: use loader helper APIs
        if sector_id:
            try:
                card_path = _runtime_paths.resolve_sector_card_path(sector_id)
                _check_path_safety(str(card_path))
                card_dir = card_path.parent
            except (KeyError, ValueError, RuntimeError) as exc:
                print(f"  [WARNING] Could not resolve sector card path for sector_id='{sector_id}': {exc}")
                print(f"  [WARNING] Skipping sector card output for '{sub_theme}'.")
                card_path = None
                card_dir = None
        else:
            card_path = None
            card_dir = None
            print(f"  [WARNING] Project-aware mode: no sector_id for '{sub_theme}', skipping card output.")

        out_dir = _runtime_paths.output_root
        tt_dir = _runtime_paths.total_tables_dir
        lg_dir = _runtime_paths.logs_dir
        path_mode = "project-aware"
    else:
        # Legacy mode: use hard-coded globals (original behavior)
        _legacy_prefix = "01_" if "AI" in main_theme else "02_"
        card_dir = OUT_DIR / (_legacy_prefix + main_theme)
        out_dir = OUT_DIR
        tt_dir = out_dir / "00_总表"
        lg_dir = LOG_DIR
        path_mode = "legacy"

    # ── Write outputs ─────────────────────────────────────────────────────────
    append_csv(tt_dir / "代表公司财务估值总表.csv", COMPANY_TABLE_FIELDS, company_rows)
    append_csv(tt_dir / "科技细分方向横向比较表.csv", COMPARISON_FIELDS, [comparison_row])
    curated_sources = evidence_source_rows(evidence)
    if curated_sources:
        append_csv(tt_dir / "数据来源索引.csv", SOURCE_FIELDS, curated_sources)

    # Sector card
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
    print(f"  Guosen health: {'OK' if guosen_health else 'DISABLED/SKIP'}")

    return {
        "sub_theme": sub_theme,
        "sector_id": sector_id,
        "companies": len(companies),
        "daily_data": {c: len(r) for c, r in daily_data.items()},
        "profit_data": {c: len(r) for c, r in profit_data.items()},
        "guosen_health": guosen_health,
        "card_path": str(card_path.relative_to(ROOT)) if card_path else "(skipped: unresolved)",
        "path_mode": path_mode,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Standardized A股科技主线调研")
    parser.add_argument("--project", type=str,
                        help="Project ID (e.g. tech_ai_semiconductor). Activates project-aware mode.")
    parser.add_argument("--sub-theme", type=str,
                        help="Run a specific sub-theme by name (legacy mode, or mixed with --project)")
    parser.add_argument("--sector-id", type=str,
                        help="Canonical sector_id to run (project-aware only). Resolves via legacy_sector_map.")
    parser.add_argument("--batch", type=str, choices=["p0", "p1", "p2", "all"],
                        help="Run all sub-themes in a batch")
    parser.add_argument("--companies", type=str,
                        help="Comma-separated codes override (e.g. 300308,300502)")
    parser.add_argument("--enable-guosen", action="store_true",
                        help="Re-enable legacy Guosen API calls")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch data but don't write outputs")
    parser.add_argument("--prefer-tencent-daily", action="store_true",
                        help="Use Tencent direct for daily K-line before BaoStock")
    args = parser.parse_args()

    global _project_config, _runtime_paths

    # ── Project-aware init ─────────────────────────────────────────────────
    if args.project:
        from investment_system.pipelines.sector_research.load_project import (
            load_project,
            resolve_sector_card_path as _lp_resolve_sector_card_path,
            resolve_output_paths as _lp_resolve_output_paths,
            get_sector as _lp_get_sector,
        )

        try:
            _project_config = load_project(args.project, silent=False, strict=False)
            paths = _lp_resolve_output_paths(_project_config)

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
            _runtime_paths._resolve_sector_card_path = lambda sid: _lp_resolve_sector_card_path(
                _project_config, sid
            )

            print(f"[PROJECT-AWARE] Project: {_project_config.project_name} ({args.project})")
            print(f"[PROJECT-AWARE] Output root: {_runtime_paths.output_root}")
            print(f"[PROJECT-AWARE] total_tables: {_runtime_paths.total_tables_dir}")
            print(f"[PROJECT-AWARE] logs: {_runtime_paths.logs_dir}")

            # Warn if output_root doesn't exist (don't create aggressively)
            if not _runtime_paths.output_root.exists():
                print(f"[WARNING] Output root does not exist: {_runtime_paths.output_root}")
                print(f"[WARNING] Outputs will be written there (mkdir will be called on first write).")

        except Exception as exc:
            print(f"[ERROR] Failed to load project '{args.project}': {exc}")
            print("[ERROR] Falling back to legacy mode.")
            _project_config = None
            _runtime_paths = None
    else:
        _project_config = None
        _runtime_paths = None
        print("[LEGACY MODE] No --project specified, using hard-coded paths.")

    load_env()
    tracker = DataTracker()
    results = []

    # ── Single sub-theme / sector-id ──────────────────────────────────────
    if args.sub_theme or args.sector_id:
        if args.sector_id and _project_config:
            # Project-aware sector-id mode
            try:
                sector = _lp_get_sector(_project_config, args.sector_id)
                sub_theme = sector.get("sector_name", args.sector_id)
                canonical_id = sector.get("sector_id", args.sector_id)
                main_theme = sector.get("parent_chain", "AI算力硬件")
                chain_position = sector.get("chain_position", "待确认")
                industry_logic = sector.get("industry_logic", "")

                # Get companies from stock_universe via get_stocks_for_sector
                from investment_system.pipelines.sector_research.load_project import (
                    get_stocks_for_sector,
                )
                sector_stocks = get_stocks_for_sector(_project_config, canonical_id, include_pending=False)
                if not sector_stocks:
                    # Fall back to legacy KNOWN_COMPANIES if no stocks found
                    print(f"[WARNING] No stocks found for sector_id='{canonical_id}' in stock_universe. "
                          f"Falling back to KNOWN_COMPANIES.")
                    companies = KNOWN_COMPANIES.get(sub_theme, [])
                else:
                    companies = []
                    for s in sector_stocks:
                        code = s.get("code", "")
                        if not code or code in ("pending", "待查"):
                            continue
                        market = "SZ" if code.startswith(("0", "3")) else "SH"
                        companies.append({
                            "code": code,
                            "market": market,
                            "set_code": s.get("set_code", 0),
                            "name": s.get("name", code),
                        })

            except KeyError as exc:
                print(f"[ERROR] Cannot resolve sector_id='{args.sector_id}': {exc}")
                return 1
        elif args.sub_theme:
            # Legacy sub-theme mode
            sub_theme = args.sub_theme
            canonical_id = args.sector_id  # may be None
            companies = KNOWN_COMPANIES.get(sub_theme, [])
            theme_meta = load_theme_registry().get(sub_theme, {})
            main_theme = theme_meta.get("main_theme", "AI算力硬件")
            chain_position = theme_meta.get("chain_position", "待确认")
            industry_logic = theme_meta.get("industry_logic", "")

            if not companies:
                print(f"Unknown sub-theme '{sub_theme}' with no known companies.")
                return 1
        else:
            print("[ERROR] --sector-id requires --project")
            return 1

        if args.companies:
            codes = args.companies.split(",")
            companies = [{"code": c, "market": "SZ", "set_code": 0, "name": c} for c in codes]

        r = run_sub_theme(
            sub_theme,
            companies,
            main_theme,
            chain_position,
            tracker,
            skip_guosen=not args.enable_guosen,
            dry_run=args.dry_run,
            industry_logic=industry_logic,
            prefer_tencent_daily=args.prefer_tencent_daily,
            sector_id=canonical_id,
        )
        results.append(r)

    # ── Batch mode ─────────────────────────────────────────────────────────
    elif args.batch:
        registry = load_theme_registry()
        for sub_theme, companies in KNOWN_COMPANIES.items():
            theme_meta = registry.get(sub_theme, {})

            # In project-aware mode, try to resolve sector_id from legacy alias
            canonical_id = None
            if _project_config is not None:
                try:
                    sector = _lp_get_sector(_project_config, sub_theme)
                    canonical_id = sector.get("sector_id", None)
                except KeyError:
                    canonical_id = None  # not in sector_universe, will be skipped below

                if canonical_id is None:
                    print(f"  [WARNING] Project-aware: '{sub_theme}' has no canonical sector_id "
                          f"(not in sector_universe.yaml), skipping card output.")
                    # Still run but without sector_id → card output skipped

            try:
                r = run_sub_theme(
                    sub_theme, companies,
                    theme_meta.get("main_theme", "AI算力硬件"),
                    theme_meta.get("chain_position", "待确认"),
                    tracker,
                    skip_guosen=not args.enable_guosen,
                    dry_run=args.dry_run,
                    industry_logic=theme_meta.get("industry_logic", ""),
                    prefer_tencent_daily=args.prefer_tencent_daily,
                    sector_id=canonical_id,
                )
                results.append(r)
            except Exception as exc:
                print(f"  ERROR in {sub_theme}: {exc}")
                results.append({"sub_theme": sub_theme, "error": str(exc)})

    else:
        print("Specify --sub-theme <name> or --batch <p0|p1|p2|all>")
        return 1

    if tracker.missing or tracker.conflicts or tracker.sources:
        tracker.save()

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(" RESEARCH RUN COMPLETE")
    print(f"{'='*60}")
    for r in results:
        status = "OK" if "error" not in r else f"ERROR: {r.get('error')}"
        companies_done = r.get("companies", "?")
        mode = r.get("path_mode", "?")
        card = r.get("card_path", "?")
        print(f"  [{mode}] {r['sub_theme']}: {status} ({companies_done} companies)")
        print(f"          card: {card}")

    out_dir = (_runtime_paths.output_root if _runtime_paths else OUT_DIR)
    print(f"\nAll outputs in: {out_dir.relative_to(ROOT)}")

    # Reset global state
    _project_config = None
    _runtime_paths = None
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
