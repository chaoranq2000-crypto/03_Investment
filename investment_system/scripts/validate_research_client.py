"""Validate research_client.py with real data.

Tests all public methods with actual network calls to confirm
BaoStock, Guosen, and Tencent are working end-to-end.
"""
from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from research_client import (
    ResearchClient,
    tencent_bar_direct,
    BaoStockClient,
    GuosenClient,
)

TODAY = date.today().isoformat()


def ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


def test_baostock() -> dict:
    print(f"[{ts()}] BaoStock: single session + daily + profit...")
    result = {"daily_rows": 0, "profit_rows": 0}
    with BaoStockClient(interval=1.5) as bs:
        if not bs.login_ok():
            result["login_error"] = bs._login_result
            return result
        # Test 300308
        daily = bs.daily("300308", "SZ")
        result["daily_rows"] = len(daily)
        if daily:
            result["daily_latest"] = daily[-1]

        profit = bs.profit("300308", "SZ", [2025])
        result["profit_rows"] = len(profit)
        if profit:
            result["profit_latest"] = profit[-1]
    return result


def test_guosen() -> dict:
    print(f"[{ts()}] Guosen: curl health check...")
    gs = GuosenClient()
    health = gs.health_check()
    if not health:
        return {"health": False, "reason": "curl health check failed"}
    # Try comb_hq
    hq = gs.comb_hq(["300308"], [0])
    if "_guosen_error" in hq:
        return {"health": True, "comb_hq": "failed", "detail": hq}
    return {"health": True, "comb_hq": "ok", "keys_used": gs.keys}


def test_tencent_direct() -> dict:
    print(f"[{ts()}] Tencent direct (no akshare)...")
    rows = tencent_bar_direct("sz300308")
    if rows and "_error" not in rows[0]:
        return {"ok": True, "rows": len(rows), "latest": rows[-1] if rows else None}
    return {"ok": False, "rows": rows}


def test_akshare_indicator() -> dict:
    print(f"[{ts()}] AKShare financial_indicator (non-push2his)...")
    from research_client import AKShareClient, HumanRateLimiter
    limiter = HumanRateLimiter(min_seconds=8.0, jitter=4.0)
    ak = AKShareClient(limiter=limiter)
    rows = ak.financial_indicator("300308", start_year="2025")
    if rows and "_error" not in rows[0]:
        return {"ok": True, "rows": len(rows), "latest": rows[-1] if rows else None}
    return {"ok": False, "sample": rows[:2]}


def test_full_research_client() -> dict:
    print(f"\n[{ts()}] === Full ResearchClient end-to-end ===")
    results = {}
    with ResearchClient(skip_guosen=False, baostock_interval=1.5, akshare_min_wait=8.0, akshare_jitter=4.0) as client:
        # Daily kline
        daily = client.get_daily_kline("300308", "SZ")
        results["daily"] = {"rows": len(daily), "ok": bool(daily and "_error" not in daily[0])}
        if daily:
            results["daily"]["latest"] = daily[-1]

        # Profit
        profit = client.get_profit("300308", "SZ", [2025])
        results["profit"] = {"rows": len(profit), "ok": bool(profit and "_error" not in profit[0])}
        if profit:
            results["profit"]["latest"] = profit[-1]

        # Guosen health
        results["guosen_health"] = client.guosen_health()

        # Guosen comb_hq
        hq = client.get_comb_hq(["300308", "300502"], [0, 0])
        results["guosen_hq"] = {"ok": "_guosen_error" not in hq, "keys": hq.get("_guosen_meta", {}).get("key_env", "unknown")}

        # Tencent direct via client
        tencent_rows = client.get_tencent_direct("sz300308")
        results["tencent_direct"] = {"rows": len(tencent_rows), "ok": bool(tencent_rows and "_error" not in tencent_rows[0])}

        # AKShare financial indicator
        indicator = client.get_akshare_financial_indicator("300308")
        results["akshare_indicator"] = {"rows": len(indicator), "ok": bool(indicator and "_error" not in indicator[0])}
    return results


def main() -> int:
    print("=" * 60)
    print(" research_client.py validation")
    print("=" * 60)

    all_ok = True

    # 1. BaoStock
    try:
        r = test_baostock()
        ok = r.get("daily_rows", 0) > 5 and r.get("profit_rows", 0) > 0
        print(f"  BaoStock: {'PASS' if ok else 'FAIL'} -- daily={r.get('daily_rows')} profit={r.get('profit_rows')}")
        all_ok &= ok
    except Exception as exc:
        print(f"  BaoStock: FAIL -- {exc}")
        all_ok = False

    # 2. Guosen
    try:
        r = test_guosen()
        ok = r.get("health", False)
        print(f"  Guosen:   {'PASS' if ok else 'FAIL'} -- {r}")
        all_ok &= ok
    except Exception as exc:
        print(f"  Guosen:   FAIL -- {exc}")
        all_ok = False

    # 3. Tencent direct
    try:
        r = test_tencent_direct()
        ok = r.get("ok", False)
        print(f"  Tencent:  {'PASS' if ok else 'FAIL'} -- rows={r.get('rows')} latest={r.get('latest')}")
        all_ok &= ok
    except Exception as exc:
        print(f"  Tencent:  FAIL -- {exc}")
        all_ok = False

    # 4. AKShare financial indicator
    try:
        r = test_akshare_indicator()
        ok = r.get("ok", False)
        print(f"  AKShare financial_indicator: {'PASS' if ok else 'FAIL'} -- rows={r.get('rows')}")
        all_ok &= ok
    except Exception as exc:
        print(f"  AKShare financial_indicator: FAIL -- {exc}")
        all_ok = False

    # 5. Full ResearchClient
    print()
    try:
        r = test_full_research_client()
        for key, val in r.items():
            ok = val.get("ok", val.get("rows", 0) > 0) if isinstance(val, dict) else bool(val)
            print(f"  FullClient.{key}: {'PASS' if ok else 'FAIL'} -- {val}")
            all_ok &= ok
    except Exception as exc:
        print(f"  FullClient: FAIL -- {exc}")
        all_ok = False

    print()
    print("=" * 60)
    print(f"Overall: {'ALL PASS' if all_ok else 'SOME FAILURES'}")
    print("=" * 60)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
