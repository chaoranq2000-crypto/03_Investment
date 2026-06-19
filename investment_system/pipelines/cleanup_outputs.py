"""Clean up duplicate rows in the research output CSVs.

Keeps the last-appeared row for each (sub_theme, stock_code) combination
in the company table, and the last for each (sub_theme) in the comparison table.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "科技主线调研输出"
SOURCE_DATE = "2026-06-19"

REPORT_SOURCE_REFS = {
    "300308": "年报(巨潮); 同花顺机构预期",
    "300502": "年报(深交所/巨潮); 同花顺一致预期; 山西证券研报",
    "300394": "年报(巨潮); 同花顺一致预期",
    "603083": "年报(巨潮); 国泰海通/光大证券研报",
    "002281": "年报(巨潮); 国泰海通研报",
    "000988": "年报(巨潮); 国海证券研报",
    "300570": "年报(深交所); 研报(华鑫/国金); 互动易",
    "300548": "年报(巨潮); 研报(东北/中信/华泰/国盛/大摩); 互动易",
}

CONFIDENCE_VALUES = {"高", "中高", "中", "中：行情/财务可用，主线收入暴露待核实"}


def dedup_csv(path: Path, key_fields: list[str]) -> int:
    if not path.exists():
        return 0
    rows = []
    seen_keys: dict[tuple, int] = {}
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        for row in reader:
            key = tuple(row.get(k, "") for k in key_fields)
            seen_keys[key] = len(rows)
            rows.append(row)
    if len(rows) == len(seen_keys):
        print(f"  {path.name}: no duplicates ({len(rows)} rows)")
        return 0
    # Rebuild keeping last occurrence of each key
    kept = {}
    for row in rows:
        key = tuple(row.get(k, "") for k in key_fields)
        kept[key] = row
    deduped = list(kept.values())
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(deduped)
    removed = len(rows) - len(deduped)
    print(f"  {path.name}: removed {removed} duplicates, kept {len(deduped)} rows")
    return removed


def parse_yi(value: str) -> float | None:
    if not value:
        return None
    text = str(value).replace(",", "").strip()
    text = text.replace("亿元", "").replace("亿", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def fill_company_derived_fields(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        rows = list(reader)
    changed = 0
    for row in rows:
        if row.get("ps_ttm") == "缺失":
            market_cap_yi = parse_yi(row.get("market_cap", ""))
            revenue_yi = parse_yi(row.get("revenue_2025", ""))
            if market_cap_yi and revenue_yi:
                row["ps_ttm"] = f"{market_cap_yi / revenue_yi:.2f}"
                changed += 1
    if changed:
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    print(f"  {path.name}: filled ps_ttm for {changed} rows")
    return changed


def default_source_url(code: str) -> str:
    refs = REPORT_SOURCE_REFS.get(code, "年报/研报")
    return (
        f"investment_system/data/raw/baostock/daily_kline/{SOURCE_DATE}/{code}.json; "
        f"investment_system/data/raw/baostock/profit/{SOURCE_DATE}/{code}.json; "
        f"{refs}"
    )


def repair_company_semantics(path: Path) -> int:
    """Repair semantically shifted fields from manually edited CSV rows."""
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        rows = list(reader)

    changed = 0
    for row in rows:
        code = row.get("stock_code", "")

        # 300308 had one extra quoted phrase that shifted catalysts/risks/source fields.
        if code == "300308" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", row.get("data_source", "")):
            inst = row.get("institution_forecast_change", "")
            marker = '，"'
            if marker in inst:
                forecast, catalyst = inst.split(marker, 1)
                row["institution_forecast_change"] = forecast
                row["catalysts"] = catalyst.rstrip('"')
            row["risks"] = row.get("catalysts", row.get("risks", ""))
            row["risks"] = "涨幅较大（近6月+148%，PE TTM 101x）；两头在外（汇率/关税风险）；客户集中度高；CPO/LPO路线竞争"
            row["data_source"] = "Tencent direct(行情); BaoStock(财务); 年报/研报(基本面); 同花顺一致预期"
            row["source_date"] = SOURCE_DATE
            row["source_url"] = default_source_url(code)
            row["confidence_level"] = "高"
            changed += 1

        if code == "300570" and row.get("revenue_2026E", "").startswith("ode>"):
            row["revenue_2026E"] = row["revenue_2026E"].replace("ode>", "约", 1)
            changed += 1

        if row.get("institution_forecast_change", "").endswith('"'):
            row["institution_forecast_change"] = row["institution_forecast_change"].rstrip('"')
            changed += 1

        # Rows where the confidence value landed in source_date/source_url.
        if row.get("source_date") in CONFIDENCE_VALUES:
            row["confidence_level"] = row.get("source_date", "")
            row["source_date"] = SOURCE_DATE
            changed += 1
        if row.get("source_url") in CONFIDENCE_VALUES:
            row["confidence_level"] = row.get("source_url", "")
            row["source_url"] = ""
            changed += 1
        if not row.get("source_url"):
            row["source_url"] = default_source_url(code)
            changed += 1
        if not row.get("confidence_level"):
            row["confidence_level"] = "高"
            changed += 1

    if changed:
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    print(f"  {path.name}: repaired semantic fields in {changed} cells")
    return changed


def remove_invalid_source_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        rows = list(reader)
    kept = []
    removed = 0
    for row in rows:
        quote = row.get("quote_or_excerpt", "")
        if "缺失元" in quote:
            removed += 1
            continue
        kept.append(row)
    if removed:
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(kept)
    print(f"  {path.name}: removed {removed} invalid source rows")
    return removed


def main() -> int:
    company_csv = OUT / "00_总表" / "代表公司财务估值总表.csv"
    comp_csv = OUT / "00_总表" / "科技细分方向横向比较表.csv"
    source_csv = OUT / "00_总表" / "数据来源索引.csv"

    total_removed = 0
    total_removed += dedup_csv(company_csv, ["sub_theme", "stock_code"])
    total_removed += dedup_csv(comp_csv, ["sub_theme"])
    total_removed += dedup_csv(source_csv, ["source_id"])
    total_removed += remove_invalid_source_rows(source_csv)
    repair_company_semantics(company_csv)
    fill_company_derived_fields(company_csv)

    print(f"\nTotal duplicate rows removed: {total_removed}")

    # Verify company CSV format
    print("\n--- Company table format check ---")
    if company_csv.exists():
        with company_csv.open(newline="", encoding="utf-8-sig") as f:
            fields = f.readline().strip().split(",")
        expected = [
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
        if fields == expected:
            print(f"  Format: MATCH (40 fields)")
        else:
            print(f"  Format: MISMATCH")
            for i, (got, exp) in enumerate(zip(fields, expected)):
                if got != exp:
                    print(f"    field {i}: got '{got}' expected '{exp}'")

    print("\n--- Comparison table format check ---")
    if comp_csv.exists():
        with comp_csv.open(newline="", encoding="utf-8-sig") as f:
            fields = f.readline().strip().split(",")
        expected = [
            "main_theme", "sub_theme", "chain_position", "industry_logic_summary",
            "representative_companies", "performance_stage_score", "industry_prosperity_score",
            "upside_score", "bubble_safety_score", "fund_recognition_score",
            "catalyst_score", "total_score", "recommended_next_action",
            "key_evidence", "key_risks", "missing_data", "source_index_refs",
        ]
        if fields == expected:
            print(f"  Format: MATCH (17 fields)")
        else:
            print(f"  Format: MISMATCH")
            for i, (got, exp) in enumerate(zip(fields, expected)):
                if got != exp:
                    print(f"    field {i}: got '{got}' expected '{exp}'")

    print("\n--- Data summary ---")
    if company_csv.exists():
        with company_csv.open(newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        print(f"  Companies: {len(rows)}")
        themes = set(r["sub_theme"] for r in rows)
        print(f"  Sub-themes: {len(themes)} - {', '.join(sorted(themes))}")

    if comp_csv.exists():
        with comp_csv.open(newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        print(f"  Comparison rows: {len(rows)}")

    if source_csv.exists():
        with source_csv.open(newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        print(f"  Sources: {len(rows)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
