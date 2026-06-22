"""Build project-aware dry-run outputs for formal pipeline validation.

This module generates minimal sample outputs using real evidence data
without calling external data sources or generating investment conclusions.
Outputs are restricted to the project audit dry_run directory.
"""

from __future__ import annotations

import argparse
import csv
import json
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
    load_project,
    resolve_evidence_files_for_sector,
)


DRY_RUN_MARKER = "DRY_RUN_ONLY_NOT_FOR_INVESTMENT"
SECTOR_CARD_TEMPLATE = """---
project_id: {project_id}
sector_id: {sector_id}
sector_name: {sector_name}
research_group_id: {research_group_id}
priority: {priority}
status: dry_run
generated_at: {generated_at}
source_ids: {source_ids}
evidence_ids: {evidence_ids}
dry_run_only: true
notes: {notes}
---

# {sector_name}

**状态:** 正式最小样本 dry-run

**说明:** 本文件为正式最小样本 dry-run，用于验证 pipeline，不构成投资建议。

## 1. 一句话结论

{dry_run_marker}

## 2. 产业逻辑

本 sector card 为 dry-run 输出，用于验证 output_spec schema 合规性。

## 3. 代表公司

| 股票代码 | 公司名称 | 市场 | 角色 | 数据状态 |
|---|---|---|---|---|
{company_rows}

## 4. 基本面验证

{dry_run_marker}

## 5. 估值

{dry_run_marker}

## 6. 交易热度

{dry_run_marker}

## 7. 催化剂

{dry_run_marker}

## 8. 风险与证伪信号

{dry_run_marker}

## 9. 反证检查

{dry_run_marker}

## 10. 打分

{dry_run_marker}

## 11. 最终评级

**NOT_RATED** — 本文件为 dry-run 输出，不构成投资建议。

## 12. 缺失数据

- revenue_2026E: 需从研报/公告获取
- net_profit_2026E: 需从研报/公告获取
- pe_2026E: 需从研报/公告获取

## 13. 来源索引

详见配套 source_index CSV 文件。
"""


def get_dry_run_output_dir(config: ProjectConfig) -> Path:
    return WORKSPACE_ROOT / "investment_system" / "research" / "projects" / config.project_id / "audits" / "dry_run_outputs"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_evidence_for_sector(config: ProjectConfig, sector_id: str) -> dict[str, Any]:
    """Load evidence YAML for a sector using project-aware resolver."""
    evidence_files = resolve_evidence_files_for_sector(config, sector_id)
    all_evidence = {"source_index": [], "evidence_items": []}
    
    for evidence_file in evidence_files:
        try:
            if isinstance(evidence_file, dict):
                path = evidence_file.get("_resolved_path")
            else:
                path = str(evidence_file)
            if not path or not Path(path).exists():
                continue
            with open(path, "r", encoding="utf-8") as f:
                evidence = yaml.safe_load(f) or {}
            if evidence:
                all_evidence["source_index"].extend(evidence.get("source_index", []))
                all_evidence["evidence_items"].extend(evidence.get("evidence_items", []))
        except Exception:
            continue
    
    return all_evidence


def _field_order(config: ProjectConfig, output_type: str) -> list[str]:
    contract = get_output_contract(config, output_type)
    fields: list[str] = []
    for key in ("required_fields", "optional_fields"):
        for field in contract.get(key, []) or []:
            if field not in fields:
                fields.append(field)
    return fields


def build_dry_run_records(config: ProjectConfig, sector_id: str) -> dict[str, dict[str, Any]]:
    """Build dry-run records using real evidence data."""
    sector = get_sector(config, sector_id)
    stocks = get_stocks_for_sector(config, sector_id)
    evidence = _load_evidence_for_sector(config, sector_id)
    
    generated_at = _now_iso()
    
    # Extract source_ids from evidence
    source_ids = [s.get("source_id") for s in evidence.get("source_index", []) if s.get("source_id")]
    evidence_ids = [e.get("evidence_id") for e in evidence.get("evidence_items", []) if e.get("evidence_id")]
    
    source_ids_str = ",".join(source_ids[:5]) if source_ids else "NO_SOURCE_ID"
    evidence_ids_str = ",".join(evidence_ids[:5]) if evidence_ids else "NO_EVIDENCE_ID"
    
    # Build company rows for sector card
    company_rows = []
    company_records = []
    for i, stock in enumerate(stocks[:5]):  # Limit to 5 companies
        stock_code = stock.get("stock_code", f"MOCK.{i}")
        stock_name = stock.get("stock_name", stock.get("name", f"Mock_{i}"))
        market = stock.get("market", "A股")
        role = stock.get("role", "mock")
        coverage_status = "dry_run"
        data_status = "dry_run"
        
        company_rows.append(f"| {stock_code} | {stock_name} | {market} | {role} | {data_status} |")
        company_records.append({
            "project_id": config.project_id,
            "sector_id": sector_id,
            "sector_name": sector.get("sector_name", sector_id),
            "research_group_id": sector.get("research_group_id", ""),
            "stock_code": stock_code,
            "stock_name": stock_name,
            "market": market,
            "role": role,
            "exposure_type": stock.get("exposure_type", "mock"),
            "coverage_status": coverage_status,
            "data_status": data_status,
            "financial_period": "dry_run",
            "revenue": "DRY_RUN",
            "net_profit": "DRY_RUN",
            "gross_margin": "DRY_RUN",
            "pe_ttm": "DRY_RUN",
            "pe_2026e": "DRY_RUN",
            "pe_2027e": "DRY_RUN",
            "peg": "DRY_RUN",
            "source_ids": source_ids_str,
            "evidence_ids": evidence_ids_str,
            "missing_fields": "revenue_2026E,net_profit_2026E,pe_2026E",
            "conflict_flags": "none",
            "notes": DRY_RUN_MARKER,
        })
    
    common = {
        "project_id": config.project_id,
        "sector_id": sector_id,
        "sector_name": sector.get("sector_name", sector_id),
        "research_group_id": sector.get("research_group_id", ""),
        "parent_chain": sector.get("parent_chain", "mock"),
        "chain_position": sector.get("chain_position", "mock"),
        "source_ids": source_ids_str,
        "evidence_ids": evidence_ids_str,
        "confidence_level": "dry_run",
        "generated_at": generated_at,
        "notes": DRY_RUN_MARKER,
    }
    
    return {
        "sector_card": {
            **common,
            "priority": sector.get("priority", "P0"),
            "status": "dry_run",
            "sector_name": sector.get("sector_name", sector_id),
            "company_rows": "\n".join(company_rows) if company_rows else "| - | - | - | - | - |",
            "dry_run_marker": DRY_RUN_MARKER,
        },
        "company_table": company_records if company_records else [common],
        "sector_comparison_table": {
            **common,
            "core_logic": DRY_RUN_MARKER,
            "leader_stocks": ",".join([s.get("stock_name", "") for s in stocks[:3]]),
            "elastic_stocks": ",".join([s.get("stock_name", "") for s in stocks[3:6]]),
            "prosperity_score": "5",
            "prosperity_reason": DRY_RUN_MARKER,
            "earnings_certainty_score": "5",
            "earnings_certainty_reason": DRY_RUN_MARKER,
            "valuation_score": "5",
            "valuation_reason": DRY_RUN_MARKER,
            "trading_comfort_score": "5",
            "trading_comfort_reason": DRY_RUN_MARKER,
            "catalyst_score": "5",
            "catalyst_reason": DRY_RUN_MARKER,
            "purity_score": "5",
            "purity_reason": DRY_RUN_MARKER,
            "risk_control_score": "5",
            "risk_control_reason": DRY_RUN_MARKER,
            "total_score": "5",
            "action_rating": "NOT_RATED",
            "rating_reason": DRY_RUN_MARKER,
            "suggested_action": "DRY_RUN_ONLY",
            "missing_data_flags": "revenue_2026E,net_profit_2026E,pe_2026E",
            "key_evidence": DRY_RUN_MARKER,
            "key_risk": DRY_RUN_MARKER,
        },
        "source_index": [
            {
                "project_id": config.project_id,
                "source_id": s.get("source_id", f"DRY-SOURCE-{i}"),
                "subject_type": "sector",
                "subject_id": sector_id,
                "subject_name": sector.get("sector_name", sector_id),
                "sector_id": sector_id,
                "claim_supported": s.get("title", DRY_RUN_MARKER),
                "source_type": s.get("source_type", "other"),
                "source_title": s.get("title", DRY_RUN_MARKER),
                "source_date": s.get("date", generated_at[:10]),
                "url_or_path": s.get("local_path", s.get("url", DRY_RUN_MARKER)),
                "confidence": s.get("reliability_level", "dry_run"),
                "evidence_ids": evidence_ids_str,
                "extracted_fields": "dry_run",
                "notes": DRY_RUN_MARKER,
            }
            for i, s in enumerate(evidence.get("source_index", [])[:10])
        ] if evidence.get("source_index") else [{
            "project_id": config.project_id,
            "source_id": "NO_SOURCE_ID",
            "subject_type": "sector",
            "subject_id": sector_id,
            "subject_name": sector.get("sector_name", sector_id),
            "sector_id": sector_id,
            "claim_supported": DRY_RUN_MARKER,
            "source_type": "other",
            "source_title": DRY_RUN_MARKER,
            "source_date": generated_at[:10],
            "url_or_path": DRY_RUN_MARKER,
            "confidence": "dry_run",
            "evidence_ids": evidence_ids_str,
            "extracted_fields": "dry_run",
            "notes": DRY_RUN_MARKER,
        }],
        "missing_data_log": [
            {
                "project_id": config.project_id,
                "output_type": "company_table",
                "sector_id": sector_id,
                "stock_code": stock.get("stock_code", "MOCK"),
                "stock_name": stock.get("stock_name", stock.get("name", "Mock")),
                "missing_field": field,
                "current_value": "missing",
                "severity": "high",
                "reason": DRY_RUN_MARKER,
                "source_ids": source_ids_str,
                "notes": DRY_RUN_MARKER,
            }
            for stock in (stocks[:5] or [{"stock_code": "MOCK", "stock_name": "Mock"}])
            for field in ["revenue_2026E", "net_profit_2026E", "pe_2026E"]
        ],
        "conflict_data_log": [
            {
                "project_id": config.project_id,
                "output_type": "company_table",
                "sector_id": sector_id,
                "stock_code": stock.get("stock_code", "MOCK"),
                "stock_name": stock.get("stock_name", stock.get("name", "Mock")),
                "field": "revenue_2024",
                "conflicting_values": "N/A",
                "source_ids": source_ids_str,
                "severity": "low",
                "resolution_status": "dry_run",
                "notes": DRY_RUN_MARKER,
            }
            for stock in (stocks[:2] or [{"stock_code": "MOCK", "stock_name": "Mock"}])
        ],
        "score_table": {
            **common,
            "prosperity_score": "5",
            "prosperity_reason": DRY_RUN_MARKER,
            "earnings_certainty_score": "5",
            "earnings_certainty_reason": DRY_RUN_MARKER,
            "valuation_score": "5",
            "valuation_reason": DRY_RUN_MARKER,
            "trading_comfort_score": "5",
            "trading_comfort_reason": DRY_RUN_MARKER,
            "catalyst_score": "5",
            "catalyst_reason": DRY_RUN_MARKER,
            "purity_score": "5",
            "purity_reason": DRY_RUN_MARKER,
            "risk_control_score": "5",
            "risk_control_reason": DRY_RUN_MARKER,
            "total_score": "5",
            "rating": "NOT_RATED",
            "rating_reason": DRY_RUN_MARKER,
            "data_status": "dry_run",
            "score_is_mock": True,
            "score_version": "dry_run_v1",
        },
    }


def _assert_audit_path(config: ProjectConfig, path: Path) -> None:
    """Assert path is within dry_run audit directory."""
    target = path.resolve()
    dry_run_dir = get_dry_run_output_dir(config).resolve()
    output_root = config.output_root.resolve()
    
    if not str(target).startswith(str(dry_run_dir)):
        raise RuntimeError(f"dry_run output path is outside audit dry_run dir: {target}")
    if str(target).startswith(str(output_root)):
        raise RuntimeError(f"dry_run output path would write into formal output root: {target}")


def write_dry_run_files(config: ProjectConfig, sector_id: str, records: dict[str, Any]) -> list[Path]:
    """Write dry-run output files to isolated directory."""
    out_dir = get_dry_run_output_dir(config)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    
    # CSV output types
    csv_types = ["company_table", "sector_comparison_table", "source_index", "missing_data_log", "conflict_data_log", "score_table"]
    
    for output_type in csv_types:
        filename = f"dry_run_{sector_id}_{output_type}.csv"
        path = out_dir / filename
        _assert_audit_path(config, path)
        
        field_names = _field_order(config, output_type)
        data = records.get(output_type, {})
        
        # Handle company_table which may be a list
        rows = data if isinstance(data, list) else [data]
        
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=field_names, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        written.append(path)
    
    # Sector card markdown
    card_data = records.get("sector_card", {})
    sector_name = card_data.get("sector_name", sector_id)
    card_content = SECTOR_CARD_TEMPLATE.format(
        project_id=config.project_id,
        sector_id=sector_id,
        sector_name=sector_name,
        research_group_id=card_data.get("research_group_id", ""),
        priority=card_data.get("priority", "P0"),
        generated_at=card_data.get("generated_at", _now_iso()),
        source_ids=card_data.get("source_ids", ""),
        evidence_ids=card_data.get("evidence_ids", ""),
        notes=DRY_RUN_MARKER,
        company_rows=card_data.get("company_rows", "| - | - | - | - | - |"),
        dry_run_marker=DRY_RUN_MARKER,
    )
    
    card_filename = f"dry_run_{sector_id}_sector_card.md"
    card_path = out_dir / card_filename
    _assert_audit_path(config, card_path)
    card_path.write_text(card_content, encoding="utf-8")
    written.append(card_path)
    
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build project-aware dry-run output records.")
    parser.add_argument("--project", required=True, help="Project ID")
    parser.add_argument("--sector-id", required=True, help="Canonical sector_id")
    parser.add_argument("--output-root", default=None, help="Output root (default: dry_run audit dir)")
    parser.add_argument("--clean", action="store_true", help="Remove existing dry_run files before writing.")
    parser.add_argument("--dry-run", action="store_true", help="Print records only; no files written.")
    args = parser.parse_args(argv)
    
    config = load_project(args.project, create_dirs=False, strict=False, silent=True)
    
    print(f"Dry-run builder project: {config.project_id}")
    print(f"sector_id: {args.sector_id}")
    
    try:
        records = build_dry_run_records(config, args.sector_id)
        print(f"record_count: {len(records)}")
    except Exception as e:
        print(f"ERROR building dry_run records: {e}")
        return 1
    
    if args.clean:
        dry_run_dir = get_dry_run_output_dir(config)
        if dry_run_dir.exists():
            for f in dry_run_dir.glob(f"dry_run_{args.sector_id}_*"):
                f.unlink()
                print(f"removed: {f}")
        print("clean: done")
    
    if args.dry_run:
        print("dry_run: true")
        print("No files written.")
        print(json.dumps(records, ensure_ascii=False, indent=2))
        return 0
    
    try:
        written = write_dry_run_files(config, args.sector_id, records)
        print("write_dry_run_files: true")
        for path in written:
            print(f"wrote: {path}")
    except Exception as e:
        print(f"ERROR writing dry_run files: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
