"""Runtime diagnostics for BaoStock and AKShare.

This script performs a deliberately small number of low-frequency calls:
- BaoStock: one login session, one daily-kline query, one profit query.
- AKShare: one non-Eastmoney metadata call and one Eastmoney historical call,
  both guarded by human-like rate limiting.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from investment_system.pipelines.ingest_high_speed_optical import BaoStockBatchSession  # noqa: E402
from investment_system.pipelines.rate_limited_sources import HumanRateLimiter, call_with_retries  # noqa: E402


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def summarize_table(obj: Any) -> dict[str, Any]:
    if hasattr(obj, "shape") and hasattr(obj, "columns"):
        tail = obj.tail(3).to_dict(orient="records") if len(obj) else []
        return {
            "type": type(obj).__name__,
            "shape": list(obj.shape),
            "columns": [str(c) for c in obj.columns],
            "tail": tail,
        }
    return {"type": type(obj).__name__, "repr": repr(obj)[:1000]}


def diagnose_baostock(symbol: str, market: str, interval: float) -> dict[str, Any]:
    company = {"code": symbol, "market": market, "name": "diagnostic"}
    start_date = (date.today() - timedelta(days=45)).isoformat()
    result: dict[str, Any] = {"provider": "baostock", "symbol": symbol, "market": market}
    with BaoStockBatchSession(min_interval_seconds=interval, retries=1) as session:
        result["login"] = session.login_result
        daily = session.daily(company, start_date)
        profit = session.profit(company, [date.today().year - 1, date.today().year])
    result["daily_status"] = {
        "ok": not (isinstance(daily, dict) and daily.get("error")),
        "rows": len(daily.get("rows", [])) if isinstance(daily, dict) else 0,
        "error": daily.get("error") if isinstance(daily, dict) else None,
        "message": daily.get("message") if isinstance(daily, dict) else None,
    }
    result["profit_status"] = {
        "ok": not (isinstance(profit, dict) and profit.get("error")),
        "rows": len(profit.get("rows", [])) if isinstance(profit, dict) else 0,
        "errors": profit.get("errors", []) if isinstance(profit, dict) else [],
        "error": profit.get("error") if isinstance(profit, dict) else None,
    }
    result["daily_sample"] = daily.get("rows", [])[-3:] if isinstance(daily, dict) else []
    result["profit_sample"] = profit.get("rows", [])[-3:] if isinstance(profit, dict) else []
    return result


def diagnose_akshare(symbol: str, min_wait: float, jitter: float, retries: int) -> dict[str, Any]:
    import akshare as ak

    limiter = HumanRateLimiter(min_interval_seconds=min_wait, jitter_seconds=jitter)
    result: dict[str, Any] = {
        "provider": "akshare",
        "symbol": symbol,
        "version": getattr(ak, "__version__", "unknown"),
        "policy": {
            "min_wait_seconds": min_wait,
            "jitter_seconds": jitter,
            "retries": retries,
            "note": "No full-market or high-frequency calls; diagnostics only.",
        },
    }

    sina = call_with_retries(
        "tool_trade_date_hist_sina",
        lambda: summarize_table(ak.tool_trade_date_hist_sina()),
        limiter=limiter,
        retries=retries,
    )
    result["sina_trade_dates"] = sina

    start_date = (date.today() - timedelta(days=45)).strftime("%Y%m%d")
    end_date = date.today().strftime("%Y%m%d")
    eastmoney = call_with_retries(
        "stock_zh_a_hist_eastmoney",
        lambda: summarize_table(
            ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",
            )
        ),
        limiter=limiter,
        retries=retries,
    )
    result["eastmoney_hist"] = eastmoney
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="300308")
    parser.add_argument("--market", default="SZ", choices=["SZ", "SH"])
    parser.add_argument("--baostock-interval", type=float, default=2.0)
    parser.add_argument("--akshare-min-wait", type=float, default=8.0)
    parser.add_argument("--akshare-jitter", type=float, default=4.0)
    parser.add_argument("--akshare-retries", type=int, default=1)
    args = parser.parse_args()

    output: dict[str, Any] = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "symbol": args.symbol,
        "proxy_env_note": "Proxy values are not copied into this report; check shell env separately if needed.",
    }
    output["baostock"] = diagnose_baostock(args.symbol, args.market, args.baostock_interval)
    output["akshare"] = diagnose_akshare(
        args.symbol,
        args.akshare_min_wait,
        args.akshare_jitter,
        args.akshare_retries,
    )

    out_path = ROOT / "investment_system" / "data" / "raw" / "diagnostics" / date.today().isoformat() / "data_sources_runtime.json"
    write_json(out_path, output)
    print(f"wrote {out_path}")
    print(json.dumps({k: output[k] for k in ["run_at", "symbol"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
