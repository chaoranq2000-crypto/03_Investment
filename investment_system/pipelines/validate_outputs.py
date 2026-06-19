"""Validate standardized research outputs."""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "科技主线调研输出"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)
    print(f"[FAIL] {message}")


def ok(message: str) -> None:
    print(f"[OK] {message}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sub-theme", default="高速光模块")
    parser.add_argument("--card", default="01_AI算力硬件/01_高速光模块.md")
    args = parser.parse_args()

    failures: list[str] = []
    company_csv = OUT / "00_总表" / "代表公司财务估值总表.csv"
    comparison_csv = OUT / "00_总表" / "科技细分方向横向比较表.csv"
    source_csv = OUT / "00_总表" / "数据来源索引.csv"
    card_path = OUT / args.card

    for path in [company_csv, comparison_csv, source_csv, card_path]:
        if not path.exists():
            fail(f"missing output: {path.relative_to(ROOT)}", failures)
        else:
            ok(f"exists: {path.relative_to(ROOT)}")

    if failures:
        return 1

    company_rows = [r for r in read_csv(company_csv) if r.get("sub_theme") == args.sub_theme]
    if len(company_rows) < 3:
        fail(f"{args.sub_theme}: company rows < 3", failures)
    else:
        ok(f"{args.sub_theme}: {len(company_rows)} company rows")

    for field in ["latest_price", "pct_change_1m", "pct_change_3m", "pct_change_6m", "turnover_value_20d_avg", "pe_ttm", "ps_ttm"]:
        bad = [r.get("company_name", r.get("stock_code", "")) for r in company_rows if not r.get(field) or "缺失" in r.get(field, "")]
        if bad:
            fail(f"{field} has missing values: {', '.join(bad)}", failures)
        else:
            ok(f"{field}: complete")

    date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    confidence_values = {"高", "中高", "中", "低"}
    semantic_errors = []
    for row in company_rows:
        name = row.get("company_name") or row.get("stock_code", "")
        if not date_re.fullmatch(row.get("source_date", "")):
            semantic_errors.append(f"{name}: source_date={row.get('source_date', '')}")
        if row.get("confidence_level", "") not in confidence_values:
            semantic_errors.append(f"{name}: confidence_level={row.get('confidence_level', '')}")
        if row.get("source_url", "") in confidence_values or not row.get("source_url", ""):
            semantic_errors.append(f"{name}: source_url={row.get('source_url', '')}")
        if date_re.fullmatch(row.get("data_source", "")):
            semantic_errors.append(f"{name}: data_source_is_date")
    if semantic_errors:
        fail("company CSV semantic field errors: " + "; ".join(semantic_errors), failures)
    else:
        ok("company CSV semantic fields are valid")

    source_rows = read_csv(source_csv)
    source_ids = [r.get("source_id", "") for r in source_rows]
    duplicate_ids = sorted({sid for sid in source_ids if sid and source_ids.count(sid) > 1})
    if duplicate_ids:
        fail(f"duplicate source_id: {', '.join(duplicate_ids)}", failures)
    else:
        ok("source_id values are unique")

    bad_sources = [r.get("source_id", "") for r in source_rows if "缺失元" in r.get("quote_or_excerpt", "")]
    if bad_sources:
        fail(f"invalid source excerpts contain 缺失元: {', '.join(bad_sources)}", failures)
    else:
        ok("no invalid 缺失元 source excerpts")

    comparison_rows = [r for r in read_csv(comparison_csv) if r.get("sub_theme") == args.sub_theme]
    if len(comparison_rows) != 1:
        fail(f"{args.sub_theme}: expected 1 comparison row, got {len(comparison_rows)}", failures)
    else:
        ok(f"{args.sub_theme}: one comparison row")

    card_text = card_path.read_text(encoding="utf-8")
    if "缺失" in card_text:
        fail(f"{card_path.name} still contains 缺失", failures)
    else:
        ok(f"{card_path.name}: no 缺失 placeholder")

    print()
    if failures:
        print(f"Validation failed: {len(failures)} issue(s)")
        return 1
    print("Validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
