"""Legacy-only evidence override layer for standardized theme research outputs.

The automated data collectors are deliberately conservative: they only fill
fields that can be computed from market/financial databases. Business exposure,
customer binding, capacity progress, forecasts, and policy evidence are stored
as curated theme evidence under ``investment_system/research/evidence`` and
merged into the generated outputs here.

Project-aware evidence binding must use
``sector_research.load_project.resolve_evidence_files_for_sector()`` with
``run_manifest.yaml`` and ``sector_universe.yaml``. This module keeps the legacy
theme-name adapter alive for old runs only.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = ROOT / "investment_system" / "research" / "evidence"
LEGACY_ONLY_EVIDENCE_REGISTRY = True

THEME_EVIDENCE_FILES = {
    "高速光模块": "high_speed_optical_modules.yaml",
    "光器件/FAU/精密光学": "optical_components_fau_precision_optics.yaml",
}


def load_theme_evidence(sub_theme: str) -> dict[str, Any]:
    """Load curated evidence for a legacy sub-theme, if available."""
    file_name = THEME_EVIDENCE_FILES.get(sub_theme)
    if not file_name:
        return {}
    path = EVIDENCE_DIR / file_name
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data["_evidence_path"] = str(path)
    return data


def apply_company_overrides(rows: list[dict[str, str]], evidence: dict[str, Any]) -> list[dict[str, str]]:
    """Merge curated company fields into generated company rows by stock code."""
    overrides = evidence.get("company_overrides") or {}
    if not overrides:
        return rows
    for row in rows:
        code = row.get("stock_code", "")
        row.update({k: str(v) for k, v in (overrides.get(code) or {}).items()})
    return rows


def apply_comparison_override(row: dict[str, str], evidence: dict[str, Any]) -> dict[str, str]:
    """Merge curated cross-theme comparison evidence."""
    override = evidence.get("comparison_override") or {}
    if override:
        row.update({k: str(v) for k, v in override.items()})
    return row


def evidence_source_rows(evidence: dict[str, Any]) -> list[dict[str, str]]:
    """Return source index rows from curated evidence."""
    rows = evidence.get("source_rows") or []
    return [{k: str(v) for k, v in row.items()} for row in rows]


def write_evidence_logs(evidence: dict[str, Any], log_dir: Path) -> None:
    """Write curated missing/conflict/log files when the evidence supplies them."""
    logs = evidence.get("logs") or {}
    log_dir.mkdir(parents=True, exist_ok=True)
    for file_name, text in logs.items():
        (log_dir / file_name).write_text(str(text).rstrip() + "\n", encoding="utf-8")


def card_markdown(evidence: dict[str, Any]) -> str:
    """Return curated card markdown only when evidence is research-grade."""
    if str(evidence.get("grade", "")).lower() != "research":
        return ""
    text = evidence.get("card_markdown")
    return str(text).rstrip() + "\n" if text else ""


def export_current_outputs_to_evidence(
    company_csv: Path,
    comparison_csv: Path,
    source_csv: Path,
    card_path: Path,
    evidence_path: Path,
) -> None:
    """Create a theme evidence YAML from the current output files.

    This is intentionally narrow and used to migrate manually enriched outputs
    into a reproducible input layer.
    """
    with company_csv.open(newline="", encoding="utf-8-sig") as f:
        company_rows = list(csv.DictReader(f))
    with comparison_csv.open(newline="", encoding="utf-8-sig") as f:
        comparison_rows = list(csv.DictReader(f))
    with source_csv.open(newline="", encoding="utf-8-sig") as f:
        source_rows = list(csv.DictReader(f))

    company_overrides = {}
    for row in company_rows:
        code = row["stock_code"]
        company_overrides[code] = {
            key: value
            for key, value in row.items()
            if key
            not in {
                "stock_code",
                "company_name",
                "main_theme",
                "sub_theme",
                "chain_position",
                "market_cap",
                "latest_price",
                "pct_change_1m",
                "pct_change_3m",
                "pct_change_6m",
                "turnover_value_20d_avg",
                "relative_strength_vs_index",
                "revenue_2024",
                "revenue_2025",
                "net_profit_2024",
                "net_profit_2025",
                "gross_margin_latest",
                "net_margin_latest",
                "pe_ttm",
                "ps_ttm",
            }
        }

    evidence = {
        "sub_theme": "高速光模块",
        "grade": "research",
        "description": "Curated evidence migrated from the manually enriched high-speed optical module output.",
        "company_overrides": company_overrides,
        "comparison_override": comparison_rows[0] if comparison_rows else {},
        "source_rows": source_rows,
        "logs": {
            "缺失数据清单.md": "# 缺失数据清单\n\n## 已自动补充\n\n高速光模块主要缺失字段已迁移到结构化 evidence 层，并由 run_research.py 自动合并。\n\n## 仍需工具核查\n\n| 数据项 | 当前状态 | 获取方式 |\n|---|---|---|\n| 各公司PE/PB精确历史分位 | 定性高估，需可验证公开来源或用户提供数据 | 公开估值页面、券商研报或用户提供数据 |\n| 太辰光Q1负增长原因 | 待核实 | 互动易/业绩说明会 |\n| CPO/OCS对可插拔光模块替代节奏 | 定性风险，需跟踪 | 头部CSP公告/研报 |",
            "冲突数据清单.md": "# 冲突数据清单\n\n暂未发现跨来源数据冲突；AKShare Eastmoney端点不稳定已作为数据源状态记录。",
        },
        "card_markdown": card_path.read_text(encoding="utf-8"),
    }

    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    with evidence_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(evidence, f, allow_unicode=True, sort_keys=False, width=120)



