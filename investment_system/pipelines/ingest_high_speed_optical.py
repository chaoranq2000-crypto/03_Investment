"""Ingest data for the high-speed optical module research card.

Sources follow investment_system/docs/data_source_configuration.md:
- realtime quote, fund flow, financial statements: Guosen API
- daily kline: BaoStock
"""
from __future__ import annotations

import csv
import importlib.util
import json
import os
import argparse
import subprocess
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parents[2]
TODAY = date.today().isoformat()
LOCAL_ENV = ROOT / "investment_system" / "config" / ".env.local"
GUOSEN_MARKET_SCRIPT = ROOT / ".codex" / "skills" / "gs-stock-market-query" / "scripts" / "get_data.py"
GUOSEN_FINANCIAL_SCRIPT = ROOT / ".codex" / "skills" / "gs-stock-financial-query" / "scripts" / "get_data.py"
GUOSEN_BASE_URL = "https://dgzt.guosen.com.cn/skills"
GUOSEN_SOFT_NAME = "goldsun_skills"
GUOSEN_KEY_ENVS = ["GS_API_KEY", "GS_API_KEY_BACKUP"]


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


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_call(label: str, func):
    try:
        return func()
    except Exception as exc:
        return {"error": type(exc).__name__, "message": str(exc), "label": label}


def guosen_request(endpoint: str, params: dict[str, Any], skill_name: str, timeout: int) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    for key_env in GUOSEN_KEY_ENVS:
        api_key = os.environ.get(key_env)
        if not api_key:
            attempts.append({"key_env": key_env, "error": "missing_env"})
            continue
        request_params = {
            **params,
            "softName": GUOSEN_SOFT_NAME,
            "apiKey": api_key,
            "skillName": skill_name,
        }
        url = f"{GUOSEN_BASE_URL}{endpoint}?{urlencode(request_params)}"
        result = subprocess.run(
            ["curl.exe", "-s", "-k", "--connect-timeout", "20", "--max-time", str(timeout), url],
            capture_output=True,
            text=True,
            timeout=timeout + 10,
            encoding="utf-8",
            errors="ignore",
        )
        attempt: dict[str, Any] = {"key_env": key_env, "returncode": result.returncode}
        if result.stderr:
            attempt["stderr"] = result.stderr[:300]
        if result.returncode != 0:
            attempt["error"] = "curl_failed"
            attempts.append(attempt)
            continue
        if not result.stdout.strip():
            attempt["error"] = "empty_response"
            attempts.append(attempt)
            continue
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            attempt["error"] = "invalid_json"
            attempt["raw"] = result.stdout[:500]
            attempts.append(attempt)
            continue
        if isinstance(data, dict) and data.get("error"):
            attempt["error"] = data.get("error")
            attempt["response"] = data
            attempts.append(attempt)
            continue
        if isinstance(data, dict):
            data["_request_meta"] = {
                "key_env": key_env,
                "attempted_key_envs": [a["key_env"] for a in attempts] + [key_env],
            }
        return data
    return {"error": "all_guosen_keys_failed", "attempts": attempts}


def guosen_market(dataset: str, params: dict[str, Any], timeout: int) -> dict[str, Any]:
    endpoint_map = {
        "comb_hq": "/gsnews/market/agentbot/queryCombHQ/1.0",
        "fund_flow_20": "/gsnews/market/agentbot/queryFundFlow/1.0",
        "related_comb": "/gsnews/market/agentbot/queryRelatedCombHQ/1.0",
    }
    return guosen_request(endpoint_map[dataset], params, "gs-stock-market-query", timeout)


def guosen_financial(statement: str, company: dict[str, Any], timeout: int, count: int = 4) -> dict[str, Any]:
    endpoint_map = {
        "income_q0": "/gsnews/gsf10/financial/incomeStatement/1.0",
        "balance_q0": "/gsnews/gsf10/financial/balanceSheet/1.0",
        "cashflow_q0": "/gsnews/gsf10/financial/cashFlowStatement/1.0",
    }
    return guosen_request(
        endpoint_map[statement],
        {
            "code": company["code"],
            "market": company["market"],
            "reportType": "Q0",
            "count": str(count),
        },
        "gs-stock-financial-query",
        timeout,
    )


def query_baostock_daily(company: dict[str, Any], start_date: str) -> dict[str, Any]:
    import baostock as bs

    prefix = "sh" if company["market"] == "SH" else "sz"
    bs_code = f"{prefix}.{company['code']}"
    fields = "date,code,open,high,low,close,preclose,volume,amount,turn,pctChg"
    login = bs.login()
    try:
        if login.error_code != "0":
            return {"error": login.error_code, "message": login.error_msg}
        rs = bs.query_history_k_data_plus(
            bs_code,
            fields,
            start_date=start_date,
            end_date=TODAY,
            frequency="d",
            adjustflag="3",
        )
        rows: list[dict[str, str]] = []
        while rs.error_code == "0" and rs.next():
            rows.append(dict(zip(rs.fields, rs.get_row_data())))
        if rs.error_code != "0":
            return {"error": rs.error_code, "message": rs.error_msg, "rows": rows}
        return {"source": "baostock", "code": bs_code, "fields": rs.fields, "rows": rows}
    finally:
        bs.logout()


def query_baostock_profit(company: dict[str, Any], years: list[int]) -> dict[str, Any]:
    import baostock as bs

    prefix = "sh" if company["market"] == "SH" else "sz"
    bs_code = f"{prefix}.{company['code']}"
    login = bs.login()
    rows: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    try:
        if login.error_code != "0":
            return {"error": login.error_code, "message": login.error_msg}
        for year in years:
            for quarter in [1, 2, 3, 4]:
                rs = bs.query_profit_data(code=bs_code, year=year, quarter=quarter)
                if rs.error_code != "0":
                    errors.append({"year": str(year), "quarter": str(quarter), "error": rs.error_msg})
                    continue
                while rs.next():
                    record = dict(zip(rs.fields, rs.get_row_data()))
                    record["year"] = str(year)
                    record["quarter"] = str(quarter)
                    rows.append(record)
        return {"source": "baostock", "code": bs_code, "rows": rows, "errors": errors}
    finally:
        bs.logout()


class BaoStockBatchSession:
    """Single-login BaoStock session with slow, retryable batch queries."""

    def __init__(self, min_interval_seconds: float = 2.0, retries: int = 2) -> None:
        import baostock as bs

        self.bs = bs
        self.min_interval_seconds = min_interval_seconds
        self.retries = retries
        self.login_result: dict[str, str] = {}
        self._last_call = 0.0

    def __enter__(self) -> "BaoStockBatchSession":
        login = self.bs.login()
        self.login_result = {"error_code": login.error_code, "error_msg": login.error_msg}
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.bs.logout()

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last_call if self._last_call else None
        if elapsed is not None and elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)
        self._last_call = time.monotonic()

    def _call(self, label: str, func):
        attempts: list[dict[str, str]] = []
        for attempt in range(1, self.retries + 2):
            self._wait()
            try:
                return func()
            except Exception as exc:
                attempts.append({"attempt": str(attempt), "error_type": type(exc).__name__, "message": str(exc)})
                if attempt <= self.retries:
                    time.sleep(self.min_interval_seconds * attempt)
        return {"error": "baostock_call_failed", "label": label, "attempts": attempts}

    def daily(self, company: dict[str, Any], start_date: str) -> dict[str, Any]:
        def do_query() -> dict[str, Any]:
            prefix = "sh" if company["market"] == "SH" else "sz"
            bs_code = f"{prefix}.{company['code']}"
            fields = "date,code,open,high,low,close,preclose,volume,amount,turn,pctChg"
            rs = self.bs.query_history_k_data_plus(
                bs_code,
                fields,
                start_date=start_date,
                end_date=TODAY,
                frequency="d",
                adjustflag="3",
            )
            rows: list[dict[str, str]] = []
            while rs.error_code == "0" and rs.next():
                rows.append(dict(zip(rs.fields, rs.get_row_data())))
            if rs.error_code != "0":
                return {"error": rs.error_code, "message": rs.error_msg, "rows": rows}
            return {"source": "baostock", "code": bs_code, "fields": rs.fields, "rows": rows}

        if self.login_result.get("error_code") != "0":
            return {"error": self.login_result.get("error_code"), "message": self.login_result.get("error_msg")}
        return self._call(f"daily:{company['code']}", do_query)

    def profit(self, company: dict[str, Any], years: list[int]) -> dict[str, Any]:
        def do_query() -> dict[str, Any]:
            prefix = "sh" if company["market"] == "SH" else "sz"
            bs_code = f"{prefix}.{company['code']}"
            rows: list[dict[str, str]] = []
            errors: list[dict[str, str]] = []
            for year in years:
                for quarter in [1, 2, 3, 4]:
                    self._wait()
                    rs = self.bs.query_profit_data(code=bs_code, year=year, quarter=quarter)
                    if rs.error_code != "0":
                        errors.append({"year": str(year), "quarter": str(quarter), "error": rs.error_msg})
                        continue
                    while rs.next():
                        record = dict(zip(rs.fields, rs.get_row_data()))
                        record["year"] = str(year)
                        record["quarter"] = str(quarter)
                        rows.append(record)
            return {"source": "baostock", "code": bs_code, "rows": rows, "errors": errors}

        if self.login_result.get("error_code") != "0":
            return {"error": self.login_result.get("error_code"), "message": self.login_result.get("error_msg")}
        return self._call(f"profit:{company['code']}", do_query)


def pct_change(rows: list[dict[str, str]], periods: int) -> str:
    if len(rows) <= periods:
        return "缺失"
    latest = float(rows[-1]["close"])
    base = float(rows[-1 - periods]["close"])
    if base == 0:
        return "缺失"
    return f"{(latest / base - 1) * 100:.2f}%"


def amount_avg(rows: list[dict[str, str]], periods: int = 20) -> str:
    vals = [float(r["amount"]) for r in rows[-periods:] if r.get("amount")]
    if not vals:
        return "缺失"
    return f"{sum(vals) / len(vals) / 100000000:.2f}亿元"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-guosen", action="store_true", help="skip Guosen calls when endpoint is unstable")
    parser.add_argument("--limit", type=int, default=0, help="limit company count for testing")
    parser.add_argument("--guosen-timeout", type=int, default=90, help="curl max-time for each Guosen request")
    parser.add_argument("--baostock-interval", type=float, default=2.0, help="seconds between BaoStock queries")
    args = parser.parse_args()

    load_dotenv(LOCAL_ENV)
    if not args.skip_guosen and not os.environ.get("GS_API_KEY"):
        raise RuntimeError("GS_API_KEY is not configured in environment or .env.local")

    use_guosen = not args.skip_guosen

    start_date = (date.today() - timedelta(days=220)).isoformat()
    companies = COMPANIES[: args.limit] if args.limit else COMPANIES
    run_meta = {
        "dataset": "高速光模块",
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "date": TODAY,
        "companies": companies,
        "skip_guosen": args.skip_guosen,
        "source_priority": {
            "realtime_quote": ["guosen", "akshare"],
            "daily_kline": ["baostock", "akshare", "guosen"],
            "financial_statement": ["guosen", "baostock", "akshare"],
            "fund_flow": ["guosen", "akshare"],
        },
    }
    write_json(ROOT / "investment_system" / "data" / "raw" / "research_runs" / TODAY / "高速光模块_run_meta.json", run_meta)

    if use_guosen:
        codes = [c["code"] for c in companies]
        set_codes = [c["set_code"] for c in companies]
        write_json(
            ROOT / "investment_system" / "data" / "raw" / "guosen" / "comb_hq" / TODAY / "高速光模块.json",
            guosen_market(
                "comb_hq",
                {
                    "code": ",".join(codes),
                    "setCode": ",".join(str(sc) for sc in set_codes),
                    "target": "0",
                },
                args.guosen_timeout,
            ),
        )

    summary_rows: list[dict[str, str]] = []
    with BaoStockBatchSession(min_interval_seconds=args.baostock_interval) as baostock:
        write_json(
            ROOT / "investment_system" / "data" / "raw" / "baostock" / "session" / TODAY / "login.json",
            baostock.login_result,
        )
        for company in companies:
            code = company["code"]
            set_code = company["set_code"]
            row: dict[str, str] = {
                "stock_code": code,
                "company_name": company["name"],
                "main_theme": "AI算力硬件",
                "sub_theme": "高速光模块",
                "chain_position": "中游核心",
            }

            daily = baostock.daily(company, start_date)
            write_json(ROOT / "investment_system" / "data" / "raw" / "baostock" / "daily_kline" / TODAY / f"{code}.json", daily)
            profit = baostock.profit(company, [2024, 2025, 2026])
            write_json(ROOT / "investment_system" / "data" / "raw" / "baostock" / "profit" / TODAY / f"{code}.json", profit)
            daily_rows = daily.get("rows", []) if isinstance(daily, dict) else []
            row["pct_change_1m"] = pct_change(daily_rows, 20)
            row["pct_change_3m"] = pct_change(daily_rows, 60)
            row["pct_change_6m"] = pct_change(daily_rows, 120)
            row["turnover_value_20d_avg"] = amount_avg(daily_rows, 20)

            if use_guosen:
                results = {
                    "fund_flow_20": guosen_market(
                        "fund_flow_20",
                        {"code": code, "setCode": str(set_code), "period": "20"},
                        args.guosen_timeout,
                    ),
                    "related_comb": guosen_market(
                        "related_comb",
                        {"code": code, "setCode": str(set_code), "target": "0"},
                        args.guosen_timeout,
                    ),
                    "income_q0": guosen_financial("income_q0", company, args.guosen_timeout),
                    "balance_q0": guosen_financial("balance_q0", company, args.guosen_timeout),
                    "cashflow_q0": guosen_financial("cashflow_q0", company, args.guosen_timeout),
                }
                for name, result in results.items():
                    write_json(ROOT / "investment_system" / "data" / "raw" / "guosen" / name / TODAY / f"{code}.json", result)
                    row[f"{name}_status"] = "error" if isinstance(result, dict) and result.get("error") else "ok"
            else:
                row["guosen_status"] = "skipped"

            summary_rows.append(row)

    processed = ROOT / "investment_system" / "data" / "processed" / "theme_research" / TODAY
    processed.mkdir(parents=True, exist_ok=True)
    out_csv = processed / "高速光模块_company_market_summary.csv"
    with out_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"wrote {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
