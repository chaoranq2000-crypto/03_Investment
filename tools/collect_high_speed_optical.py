import csv
import importlib.util
import json
import os
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "科技主线调研输出" / "98_原始数据" / "高速光模块"
MEMORY = ROOT / "memory.md"


COMPANIES = [
    {"code": "300308", "market": "SZ", "set_code": 0, "name": "中际旭创"},
    {"code": "300502", "market": "SZ", "set_code": 0, "name": "新易盛"},
    {"code": "300394", "market": "SZ", "set_code": 0, "name": "天孚通信"},
    {"code": "603083", "market": "SH", "set_code": 1, "name": "剑桥科技"},
    {"code": "002281", "market": "SZ", "set_code": 0, "name": "光迅科技"},
    {"code": "000988", "market": "SZ", "set_code": 0, "name": "华工科技"},
    {"code": "300570", "market": "SZ", "set_code": 0, "name": "太辰光"},
    {"code": "300548", "market": "SZ", "set_code": 0, "name": "博创科技"},
]


def load_key() -> str:
    for line in MEMORY.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("GS_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("GS_API_KEY not found in memory.md")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    os.environ["GS_API_KEY"] = load_key()
    market = load_module(
        ROOT / ".codex" / "skills" / "gs-stock-market-query" / "scripts" / "get_data.py",
        "gs_stock_market_query_get_data",
    )
    financial = load_module(
        ROOT / ".codex" / "skills" / "gs-stock-financial-query" / "scripts" / "get_data.py",
        "gs_stock_financial_query_get_data",
    )

    OUT.mkdir(parents=True, exist_ok=True)
    run_meta = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "companies": COMPANIES,
        "notes": "Raw API responses. API key intentionally not persisted.",
    }
    write_json(OUT / "run_meta.json", run_meta)

    codes = [c["code"] for c in COMPANIES]
    set_codes = [c["set_code"] for c in COMPANIES]
    write_json(OUT / "market_comb_hq.json", market.query_comb_hq(codes, set_codes))

    summary_rows = []
    for company in COMPANIES:
        code = company["code"]
        set_code = company["set_code"]
        market_code = company["market"]
        item = {"code": code, "name": company["name"], "market": market_code}

        calls = {
            "past_hq_20": lambda: market.query_past_hq(code, str(set_code), 20),
            "past_hq_60": lambda: market.query_past_hq(code, str(set_code), 60),
            "past_hq_125": lambda: market.query_past_hq(code, str(set_code), 125),
            "fund_flow_20": lambda: market.query_fund_flow(code, str(set_code), "20"),
            "related_comb": lambda: market.query_related_comb_hq(code, set_code),
            "income_q4_2024": lambda: financial.query_a_stock_income_statement(
                code, market_code, report_type="Q4", report_year="2024", count="1"
            ),
            "income_q0": lambda: financial.query_a_stock_income_statement(
                code, market_code, report_type="Q0", count="4"
            ),
            "balance_q0": lambda: financial.query_a_stock_balance_sheet(
                code, market_code, report_type="Q0", count="4"
            ),
            "cashflow_q0": lambda: financial.query_a_stock_cash_flow_statement(
                code, market_code, report_type="Q0", count="4"
            ),
        }

        for call_name, call in calls.items():
            try:
                result = call()
            except Exception as exc:
                result = {"error": type(exc).__name__, "message": str(exc)}
            write_json(OUT / f"{code}_{call_name}.json", result)
            item[f"{call_name}_status"] = "ok" if not isinstance(result, dict) or "error" not in result else "error"
        summary_rows.append(item)

    csv_path = OUT / "fetch_status.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=summary_rows[0].keys())
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"saved {len(summary_rows)} companies to {OUT}")


if __name__ == "__main__":
    main()
