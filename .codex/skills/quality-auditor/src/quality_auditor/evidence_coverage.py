"""
Evidence Coverage Audit for P0/P1 Sectors.

Performs a detailed evidence coverage analysis for all P0/P1 scoring-enabled
sectors, generating a coverage matrix and actionable recommendations.

Usage:
    python .codex/skills/quality-auditor/scripts/cli.py evidence-coverage --project tech_ai_semiconductor
    python .codex/skills/quality-auditor/scripts/cli.py evidence-coverage --project tech_ai_semiconductor --priority P0,P1
    python .codex/skills/quality-auditor/scripts/cli.py evidence-coverage --project tech_ai_semiconductor --output
    python .codex/skills/quality-auditor/scripts/cli.py evidence-coverage --project tech_ai_semiconductor --markdown
    python .codex/skills/quality-auditor/scripts/cli.py evidence-coverage --project tech_ai_semiconductor --csv

Exit codes:
    0  success, no issues
    1  project not found
    2  validation error (ERROR-level issues found)
    3  warnings only
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

# Import from load_project
from investment_system.core.project_loader import (
    WORKSPACE_ROOT,
    load_project,
    get_stocks_for_sector,
    resolve_evidence_files_for_sector,
)


# ── Coverage Requirements ──────────────────────────────────────────────────────

SECTOR_CARD_MINIMUM_REQUIREMENTS = {
    "sector_logic": {
        "name": "产业逻辑",
        "min_count": 1,
        "evidence_types": ["sector_level_claim", "industry_logic", "comparison_bundle"],
        "description": "至少1条产业逻辑证据",
    },
    "stock_positioning": {
        "name": "股票池/公司定位",
        "min_count": 3,
        "evidence_types": ["company_evidence", "company_bundle"],
        "description": "至少3家公司有证据",
    },
    "revenue_or_profit": {
        "name": "收入或利润验证",
        "min_count": 3,
        "evidence_types": ["revenue_data", "profit_data", "financial_data"],
        "description": "至少3家公司有收入或利润证据",
    },
    "valuation": {
        "name": "估值字段",
        "min_count": 1,
        "evidence_types": ["pe_data", "ps_data", "peg_data", "market_cap_data"],
        "description": "必须有估值来源或进入missing_data_log",
    },
    "trading_heat": {
        "name": "交易热度字段",
        "min_count": 1,
        "evidence_types": ["price_data", "turnover_data", "momentum_data"],
        "description": "必须有交易热度来源或进入missing_data_log",
    },
    "risk": {
        "name": "风险字段",
        "min_count": 1,
        "evidence_types": ["risk_evidence", "risk_bundle"],
        "description": "至少1条可追溯风险证据",
    },
}


# ── Coverage Analysis ──────────────────────────────────────────────────────────

def analyze_evidence_file(evidence_path: Path, sector_id: str | None = None) -> dict[str, Any]:
    """
    Analyze an evidence YAML file and extract coverage metadata.
    
    Returns:
        dict with keys:
        - source_count: number of source_index entries
        - evidence_item_count: number of evidence_items entries
        - company_evidence_count: evidence items of type company
        - sector_evidence_count: evidence items of type sector
        - has_revenue_evidence: bool
        - has_profit_evidence: bool
        - has_valuation_evidence: bool
        - has_trading_evidence: bool
        - has_risk_evidence: bool
        - evidence_item_ids: list of evidence_id strings
        - source_ids: list of source_id strings
    """
    if not evidence_path.exists():
        return {
            "source_count": 0,
            "evidence_item_count": 0,
            "company_evidence_count": 0,
            "sector_evidence_count": 0,
            "has_revenue_evidence": False,
            "has_profit_evidence": False,
            "has_valuation_evidence": False,
            "has_trading_evidence": False,
            "has_risk_evidence": False,
            "evidence_item_ids": [],
            "source_ids": [],
        }
    
    with evidence_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    
    source_index = data.get("source_index", [])
    raw_evidence_items = data.get("evidence_items", [])
    if sector_id:
        evidence_items = [
            item for item in raw_evidence_items
            if item.get("sector_id") == sector_id
        ]
    else:
        evidence_items = raw_evidence_items
    
    # Count by subject_type
    company_count = sum(
        1 for e in evidence_items
        if e.get("subject_type") == "company"
    )
    sector_count = sum(
        1 for e in evidence_items
        if e.get("subject_type") == "sector"
    )
    
    # Check for evidence types in metrics_supported
    evidence_types_found = set()
    for e in evidence_items:
        metrics = e.get("metrics_supported", []) or []
        for m in metrics:
            if "revenue" in m.lower():
                evidence_types_found.add("revenue")
            if "profit" in m.lower() or "net_profit" in m.lower():
                evidence_types_found.add("profit")
            if "pe" in m.lower() or "ps" in m.lower() or "peg" in m.lower() or "valuation" in m.lower():
                evidence_types_found.add("valuation")
            if "turnover" in m.lower() or "price" in m.lower() or "momentum" in m.lower():
                evidence_types_found.add("trading")
            if "risk" in m.lower():
                evidence_types_found.add("risk")
    
    # Also check claim text for evidence type hints
    for e in evidence_items:
        claim = e.get("claim", "").lower()
        if "revenue" in claim or "收入" in claim:
            evidence_types_found.add("revenue")
        if "profit" in claim or "净利润" in claim or "利润" in claim:
            evidence_types_found.add("profit")
        if "pe" in claim or "估值" in claim or "市盈率" in claim:
            evidence_types_found.add("valuation")
        if "turnover" in claim or "换手" in claim or "成交" in claim:
            evidence_types_found.add("trading")
        if "risk" in claim or "风险" in claim:
            evidence_types_found.add("risk")
    
    return {
        "source_count": len(source_index),
        "evidence_item_count": len(evidence_items),
        "company_evidence_count": company_count,
        "sector_evidence_count": sector_count,
        "has_revenue_evidence": "revenue" in evidence_types_found,
        "has_profit_evidence": "profit" in evidence_types_found,
        "has_valuation_evidence": "valuation" in evidence_types_found,
        "has_trading_evidence": "trading" in evidence_types_found,
        "has_risk_evidence": "risk" in evidence_types_found,
        "evidence_item_ids": [e.get("evidence_id", "") for e in evidence_items],
        "source_ids": [s.get("source_id", "") for s in source_index],
    }


def check_sector_coverage(
    config,
    sector: dict[str, Any],
) -> dict[str, Any]:
    """
    Check evidence coverage for a single sector.
    
    Returns a coverage status dict with:
    - sector_id, sector_name, priority, scoring_enabled
    - stock_count, stock_coverage_status
    - evidence_file_count, evidence_files
    - source_count, evidence_item_count
    - has_sector_logic_evidence
    - has_company_revenue_evidence
    - has_company_profit_evidence
    - has_order_or_customer_evidence
    - has_valuation_evidence
    - has_trading_heat_evidence
    - has_risk_evidence
    - coverage_status: ok / partial / missing
    - blocking_reason
    - recommended_next_action
    """
    sector_id = sector.get("sector_id", "")
    sector_name = sector.get("sector_name", "")
    priority = sector.get("priority", "P9")
    scoring_enabled = sector.get("scoring_enabled", False)
    
    # Get stocks for this sector
    try:
        stocks = get_stocks_for_sector(config, sector_id)
        stock_count = len(stocks)
    except Exception:
        stock_count = 0
        stocks = []
    
    # Get evidence files for this sector
    try:
        evidence_files = resolve_evidence_files_for_sector(config, sector_id)
        evidence_file_count = len(evidence_files)
    except Exception:
        evidence_files = []
        evidence_file_count = 0
    
    # Aggregate evidence metrics
    total_source_count = 0
    total_evidence_item_count = 0
    total_company_evidence_count = 0
    has_sector_logic = False
    has_revenue = False
    has_profit = False
    has_order_or_customer = False
    has_valuation = False
    has_trading = False
    has_risk = False
    all_evidence_ids = []
    all_source_ids = []
    file_details = []
    
    for ef in evidence_files:
        resolved_path = Path(ef.get("_resolved_path", ""))
        analysis = analyze_evidence_file(resolved_path, sector_id=sector_id)
        
        total_source_count += analysis["source_count"]
        total_evidence_item_count += analysis["evidence_item_count"]
        total_company_evidence_count += analysis["company_evidence_count"]
        
        if analysis["sector_evidence_count"] > 0:
            has_sector_logic = True
        
        if analysis["has_revenue_evidence"]:
            has_revenue = True
        if analysis["has_profit_evidence"]:
            has_profit = True
        if analysis["has_valuation_evidence"]:
            has_valuation = True
        if analysis["has_trading_evidence"]:
            has_trading = True
        if analysis["has_risk_evidence"]:
            has_risk = True
        
        # Check for order/customer evidence in claims
        for item_id in analysis["evidence_item_ids"]:
            if item_id:
                all_evidence_ids.append(item_id)
        
        all_source_ids.extend(analysis["source_ids"])
        
        file_details.append({
            "path": ef.get("path", ""),
            "exists": ef.get("exists", False),
            "source_count": analysis["source_count"],
            "evidence_item_count": analysis["evidence_item_count"],
        })
    
    # Check order/customer evidence from evidence items
    # (simplified: check if any company evidence mentions customer/order)
    for ef in evidence_files:
        resolved_path = Path(ef.get("_resolved_path", ""))
        if resolved_path.exists():
            with resolved_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            evidence_items = data.get("evidence_items", [])
            for item in evidence_items:
                if item.get("sector_id") != sector_id:
                    continue
                if item.get("subject_type") == "company":
                    claim = item.get("claim", "").lower()
                    if any(kw in claim for kw in ["客户", "customer", "订单", "order", "contract"]):
                        has_order_or_customer = True
                        break
    
    # Determine stock coverage status
    if stock_count == 0:
        stock_status = "no_stocks"
    elif stock_count < 5:
        stock_status = "thin"
    else:
        stock_status = "adequate"
    
    # Determine overall coverage status
    blocking_issues = []
    
    if evidence_file_count == 0:
        blocking_issues.append("no_evidence_files")
    elif not has_sector_logic:
        blocking_issues.append("no_sector_logic")
    
    if total_company_evidence_count < 3:
        blocking_issues.append("insufficient_company_evidence")
    
    if not has_revenue and not has_profit:
        blocking_issues.append("no_financial_evidence")
    
    if not has_valuation:
        blocking_issues.append("no_valuation_evidence")
    
    if not has_trading:
        blocking_issues.append("no_trading_evidence")
    
    if not has_risk:
        blocking_issues.append("no_risk_evidence")
    
    if blocking_issues:
        if len(blocking_issues) >= 4:
            coverage_status = "missing"
        else:
            coverage_status = "partial"
    else:
        coverage_status = "ok"
    
    # Build blocking reason
    blocking_reason_map = {
        "no_evidence_files": "无evidence文件绑定",
        "no_sector_logic": "无产业逻辑证据",
        "insufficient_company_evidence": f"仅{total_company_evidence_count}家公司有证据(需要>=3)",
        "no_financial_evidence": "无收入或利润证据",
        "no_valuation_evidence": "无估值来源",
        "no_trading_evidence": "无交易热度来源",
        "no_risk_evidence": "无风险证据",
    }
    blocking_reason = "; ".join(
        blocking_reason_map.get(issue, issue)
        for issue in blocking_issues
    ) if blocking_issues else "所有最低要求已满足"
    
    # Build recommended next action
    recommended_actions = []
    
    if evidence_file_count == 0:
        recommended_actions.append("创建evidence YAML文件")
    else:
        if not has_sector_logic:
            recommended_actions.append("补充产业逻辑证据")
        if total_company_evidence_count < 3:
            recommended_actions.append(f"为剩余{stock_count - total_company_evidence_count}家公司补充证据")
        if not has_revenue and not has_profit:
            recommended_actions.append("补充财务数据(年报/公告)")
        if not has_valuation:
            recommended_actions.append("补充估值数据或加入missing_data_log")
        if not has_trading:
            recommended_actions.append("补充交易热度数据或加入missing_data_log")
        if not has_risk:
            recommended_actions.append("补充风险证据")
    
    if not recommended_actions:
        recommended_action = "可进行正式sector card生成"
    else:
        recommended_action = "; ".join(recommended_actions)
    
    return {
        "sector_id": sector_id,
        "sector_name": sector_name,
        "priority": priority,
        "scoring_enabled": scoring_enabled,
        "stock_count": stock_count,
        "stock_coverage_status": stock_status,
        "evidence_file_count": evidence_file_count,
        "evidence_files": file_details,
        "source_count": total_source_count,
        "evidence_item_count": total_evidence_item_count,
        "company_evidence_count": total_company_evidence_count,
        "has_sector_logic_evidence": has_sector_logic,
        "has_company_revenue_evidence": has_revenue,
        "has_company_profit_evidence": has_profit,
        "has_order_or_customer_evidence": has_order_or_customer,
        "has_valuation_evidence": has_valuation,
        "has_trading_heat_evidence": has_trading,
        "has_risk_evidence": has_risk,
        "all_evidence_ids": all_evidence_ids,
        "all_source_ids": all_source_ids,
        "coverage_status": coverage_status,
        "blocking_reason": blocking_reason,
        "recommended_next_action": recommended_action,
    }


def run_audit(
    config,
    priorities: list[str] | None = None,
) -> dict[str, Any]:
    """
    Run the evidence coverage audit for all P0/P1 sectors.
    
    Args:
        config: loaded ProjectConfig
        priorities: list of priorities to include (e.g., ["P0", "P1"])
                    if None, defaults to ["P0", "P1"]
    
    Returns:
        dict with audit results including:
        - timestamp, project_id
        - sectors_checked
        - sector_coverage: list of per-sector coverage results
        - summary: aggregated statistics
        - errors, warnings, info lists
    """
    if priorities is None:
        priorities = ["P0", "P1"]
    
    priorities_set = set(priorities)
    
    sectors = config.raw.get("sectors", [])
    results = []
    errors = []
    warnings = []
    info_list = []
    
    # Filter to P0/P1 scoring-enabled sectors
    target_sectors = [
        s for s in sectors
        if s.get("scoring_enabled", False)
        and s.get("priority", "P9") in priorities_set
    ]
    
    for sector in target_sectors:
        sector_result = check_sector_coverage(config, sector)
        results.append(sector_result)
        
        # Add info/warnings based on coverage
        if sector_result["coverage_status"] == "missing":
            warnings.append(
                f"[{sector_result['priority']}] {sector_result['sector_id']}: "
                f"evidence coverage missing - {sector_result['blocking_reason']}"
            )
        elif sector_result["coverage_status"] == "partial":
            info_list.append(
                f"[{sector_result['priority']}] {sector_result['sector_id']}: "
                f"partial coverage - {sector_result['blocking_reason']}"
            )
        else:
            info_list.append(
                f"[{sector_result['priority']}] {sector_result['sector_id']}: "
                f"coverage OK"
            )
    
    # Sort by priority then by coverage status
    status_order = {"missing": 0, "partial": 1, "ok": 2}
    results.sort(key=lambda x: (
        x["priority"],
        status_order.get(x["coverage_status"], 3),
        x["sector_id"],
    ))
    
    # Summary statistics
    summary = {
        "total_sectors_checked": len(results),
        "p0_count": sum(1 for r in results if r["priority"] == "P0"),
        "p1_count": sum(1 for r in results if r["priority"] == "P1"),
        "ok_count": sum(1 for r in results if r["coverage_status"] == "ok"),
        "partial_count": sum(1 for r in results if r["coverage_status"] == "partial"),
        "missing_count": sum(1 for r in results if r["coverage_status"] == "missing"),
        "total_evidence_files": sum(r["evidence_file_count"] for r in results),
        "total_source_count": sum(r["source_count"] for r in results),
        "total_evidence_item_count": sum(r["evidence_item_count"] for r in results),
        "total_company_evidence_count": sum(r["company_evidence_count"] for r in results),
    }
    
    return {
        "timestamp": datetime.now().isoformat(),
        "project_id": config.project_id,
        "priorities_checked": list(priorities_set),
        "sectors_checked": len(results),
        "sector_coverage": results,
        "summary": summary,
        "errors": errors,
        "warnings": warnings,
        "info": info_list,
    }


# ── Report Generation ──────────────────────────────────────────────────────────

def generate_markdown_report(audit_result: dict[str, Any]) -> str:
    """Generate a markdown coverage plan report."""
    lines = []
    
    # Header
    lines.append("# P0/P1 Sector Evidence Coverage Plan")
    lines.append("")
    lines.append(f"**Audit Timestamp**: {audit_result['timestamp']}")
    lines.append(f"**Project**: {audit_result['project_id']}")
    lines.append(f"**Priorities Checked**: {', '.join(audit_result['priorities_checked'])}")
    lines.append("")
    
    # Summary
    summary = audit_result["summary"]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Sectors Checked | {summary['total_sectors_checked']} |")
    lines.append(f"| P0 Sectors | {summary['p0_count']} |")
    lines.append(f"| P1 Sectors | {summary['p1_count']} |")
    lines.append(f"| Coverage OK | {summary['ok_count']} |")
    lines.append(f"| Partial Coverage | {summary['partial_count']} |")
    lines.append(f"| Missing Coverage | {summary['missing_count']} |")
    lines.append(f"| Evidence Files | {summary['total_evidence_files']} |")
    lines.append(f"| Total Sources | {summary['total_source_count']} |")
    lines.append(f"| Evidence Items | {summary['total_evidence_item_count']} |")
    lines.append(f"| Company Evidence | {summary['total_company_evidence_count']} |")
    lines.append("")
    
    # Coverage matrix
    lines.append("## Evidence Coverage Matrix")
    lines.append("")
    lines.append("| Priority | Sector ID | Sector Name | Stocks | Evidence Files | Sources | Evidence Items | Company Evidence | Sector Logic | Revenue | Profit | Valuation | Trading | Risk | Status | Blocking Reason |")
    lines.append("|----------|-----------|------------|--------|----------------|--------|----------------|------------------|-------------|---------|--------|-----------|---------|------|--------|-----------------|")
    
    for r in audit_result["sector_coverage"]:
        status_icon = {
            "ok": "OK",
            "partial": "PARTIAL",
            "missing": "MISSING",
        }.get(r["coverage_status"], "?")
        
        lines.append(
            f"| {r['priority']} | {r['sector_id']} | {r['sector_name']} | "
            f"{r['stock_count']} | {r['evidence_file_count']} | "
            f"{r['source_count']} | {r['evidence_item_count']} | "
            f"{r['company_evidence_count']} | "
            f"{'Y' if r['has_sector_logic_evidence'] else 'N'} | "
            f"{'Y' if r['has_company_revenue_evidence'] else 'N'} | "
            f"{'Y' if r['has_company_profit_evidence'] else 'N'} | "
            f"{'Y' if r['has_valuation_evidence'] else 'N'} | "
            f"{'Y' if r['has_trading_heat_evidence'] else 'N'} | "
            f"{'Y' if r['has_risk_evidence'] else 'N'} | "
            f"{status_icon} | "
            f"{r['blocking_reason']} |"
        )
    
    lines.append("")
    
    # Recommendations by sector
    lines.append("## Per-Sector Recommendations")
    lines.append("")
    
    for r in audit_result["sector_coverage"]:
        if r["coverage_status"] != "ok":
            lines.append(f"### [{r['priority']}] {r['sector_name']} ({r['sector_id']})")
            lines.append("")
            lines.append(f"**Status**: {r['coverage_status'].upper()}")
            lines.append(f"**Blocking Reason**: {r['blocking_reason']}")
            lines.append(f"**Recommended Action**: {r['recommended_next_action']}")
            lines.append("")
            lines.append(f"- Stock count: {r['stock_count']}")
            lines.append(f"- Evidence files: {r['evidence_file_count']}")
            lines.append(f"- Company evidence: {r['company_evidence_count']}/3 required")
            lines.append("")
    
    # Priority ordering for evidence supplementation
    lines.append("## Evidence Supplementation Priority")
    lines.append("")
    lines.append("Recommended order for evidence supplementation:")
    lines.append("")
    
    priority_order = []
    for r in audit_result["sector_coverage"]:
        if r["coverage_status"] != "ok":
            priority_order.append(f"{r['priority']}: {r['sector_id']} - {r['blocking_reason']}")
    
    for i, item in enumerate(priority_order, 1):
        lines.append(f"{i}. {item}")
    
    lines.append("")
    
    # Conclusion
    lines.append("## Conclusion")
    lines.append("")
    
    if summary["missing_count"] > 0:
        lines.append(f"**{summary['missing_count']} sectors** require complete evidence collection before formal research generation.")
    
    if summary["partial_count"] > 0:
        lines.append(f"**{summary['partial_count']} sectors** have partial coverage and need targeted evidence supplementation.")
    
    if summary["ok_count"] > 0:
        lines.append(f"**{summary['ok_count']} sectors** have sufficient coverage for formal research generation.")
    
    lines.append("")
    lines.append("### Next Steps")
    lines.append("")
    lines.append("1. Complete evidence collection for MISSING coverage sectors")
    lines.append("2. Address blocking reasons for PARTIAL coverage sectors")
    lines.append("3. Consider starting formal research generation for OK coverage sectors")
    lines.append("")
    
    return "\n".join(lines)


def generate_csv_matrix(audit_result: dict[str, Any]) -> str:
    """Generate a CSV coverage matrix."""
    rows = []
    
    # Header
    header = [
        "priority", "sector_id", "sector_name",
        "stock_count", "evidence_file_count", "source_count",
        "evidence_item_count", "company_evidence_count",
        "has_sector_logic_evidence",
        "has_company_revenue_evidence",
        "has_company_profit_evidence",
        "has_order_or_customer_evidence",
        "has_valuation_evidence",
        "has_trading_heat_evidence",
        "has_risk_evidence",
        "coverage_status",
        "blocking_reason",
        "recommended_next_action",
    ]
    rows.append(header)
    
    for r in audit_result["sector_coverage"]:
        row = [
            r["priority"],
            r["sector_id"],
            r["sector_name"],
            r["stock_count"],
            r["evidence_file_count"],
            r["source_count"],
            r["evidence_item_count"],
            r["company_evidence_count"],
            "Y" if r["has_sector_logic_evidence"] else "N",
            "Y" if r["has_company_revenue_evidence"] else "N",
            "Y" if r["has_company_profit_evidence"] else "N",
            "Y" if r["has_order_or_customer_evidence"] else "N",
            "Y" if r["has_valuation_evidence"] else "N",
            "Y" if r["has_trading_heat_evidence"] else "N",
            "Y" if r["has_risk_evidence"] else "N",
            r["coverage_status"],
            r["blocking_reason"],
            r["recommended_next_action"],
        ]
        rows.append(row)
    
    return "\n".join(",".join(f'"{cell}"' if ',' in str(cell) else str(cell) for cell in row) for row in rows)


# ── CLI Entry Point ───────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit P0/P1 sector evidence coverage.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python .codex/skills/quality-auditor/scripts/cli.py evidence-coverage "
            "--project tech_ai_semiconductor\n"
            "  python .codex/skills/quality-auditor/scripts/cli.py evidence-coverage "
            "--project tech_ai_semiconductor --priority P0,P1\n"
            "  python .codex/skills/quality-auditor/scripts/cli.py evidence-coverage "
            "--project tech_ai_semiconductor --output\n"
        ),
    )
    parser.add_argument("--project", type=str, required=True)
    parser.add_argument(
        "--priority",
        type=str,
        default="P0,P1",
        help="Comma-separated priorities to check (default: P0,P1)",
    )
    parser.add_argument(
        "--output",
        action="store_true",
        help="Write output files to project audit directory",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Print markdown report to stdout",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Print CSV matrix to stdout",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON results to stdout",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress summary output",
    )
    args = parser.parse_args()
    
    # Parse priorities
    priorities = [p.strip() for p in args.priority.split(",")]
    
    # Load project
    try:
        config = load_project(args.project)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"[ERROR] Validation failed: {exc}", file=sys.stderr)
        return 2
    
    # Run audit
    audit_result = run_audit(config, priorities)
    
    # Determine exit code
    error_count = len(audit_result["errors"])
    warning_count = len(audit_result["warnings"])
    info_count = len(audit_result["info"])
    
    # Print output
    if args.json:
        # Remove verbose fields for JSON output
        json_result = {k: v for k, v in audit_result.items() if k != "sector_coverage"}
        json_result["sector_coverage"] = [
            {k: v for k, v in r.items()
             if k not in ("all_evidence_ids", "all_source_ids", "evidence_files")}
            for r in audit_result["sector_coverage"]
        ]
        print(json.dumps(json_result, ensure_ascii=False, indent=2))
    
    if args.markdown:
        print(generate_markdown_report(audit_result))
    
    if args.csv:
        print(generate_csv_matrix(audit_result))
    
    if not args.quiet:
        # Summary
        print(f"Evidence Coverage Audit: {config.project_id}")
        print(f"Priorities checked: {', '.join(priorities)}")
        print()
        print(f"Sectors checked: {audit_result['sectors_checked']}")
        print(f"  P0: {audit_result['summary']['p0_count']}")
        print(f"  P1: {audit_result['summary']['p1_count']}")
        print()
        print(f"Coverage Status:")
        print(f"  OK:      {audit_result['summary']['ok_count']}")
        print(f"  PARTIAL: {audit_result['summary']['partial_count']}")
        print(f"  MISSING: {audit_result['summary']['missing_count']}")
        print()
        
        if warning_count > 0:
            print(f"Warnings ({warning_count}):")
            for w in audit_result["warnings"]:
                print(f"  - {w}")
            print()
        
        if info_count > 0 and not args.markdown and not args.csv and not args.json:
            print(f"Info ({info_count}):")
            for i in audit_result["info"]:
                print(f"  - {i}")
            print()
    
    # Write output files if requested
    if args.output:
        # Compute PROJECTS_ROOT inline
        _PROJECTS_ROOT = Path(__file__).resolve().parents[2] / "research" / "projects"
        project_dir = _PROJECTS_ROOT / args.project
        audit_dir = project_dir / "audits"
        audit_dir.mkdir(parents=True, exist_ok=True)
        
        # Write markdown report
        md_path = audit_dir / "evidence_coverage_plan.md"
        with md_path.open("w", encoding="utf-8") as f:
            f.write(generate_markdown_report(audit_result))
        print(f"Written: {md_path}", file=sys.stderr)
        
        # Write CSV matrix
        csv_path = audit_dir / "evidence_coverage_matrix.csv"
        with csv_path.open("w", encoding="utf-8") as f:
            f.write(generate_csv_matrix(audit_result))
        print(f"Written: {csv_path}", file=sys.stderr)
    
    if error_count > 0:
        return 2
    if warning_count > 0:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
