"""Comprehensive data source connectivity diagnostic.

Tests all available endpoints across BaoStock, AKShare (multiple providers),
and Guosen API to map which sources are reachable from the current environment.

AKShare calls are rate-limited with 8-12s jitter per call. Results are
saved as structured JSON so we can build a source priority map.
"""
from __future__ import annotations

import json
import os
import random
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
TODAY = date.today().isoformat()
OUT_DIR = PROJECT_ROOT / "data" / "raw" / "diagnostics" / TODAY
OUT_DIR.mkdir(parents=True, exist_ok=True)

GUOSEN_BASE_URL = "https://dgzt.guosen.com.cn/skills"
GUOSEN_KEY_ENVS = ["GS_API_KEY", "GS_API_KEY_BACKUP"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_dotenv() -> None:
    env_file = PROJECT_ROOT / "config" / ".env.local"
    if not env_file.exists():
        env_file = REPO_ROOT / "memory.md"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def save_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


@dataclass
class RateLimiter:
    min_seconds: float = 8.0
    jitter: float = 4.0
    _last: float = field(default=0.0)

    def wait(self) -> float:
        now = time.monotonic()
        target = self.min_seconds + random.uniform(0, self.jitter)
        sleep_for = target if not self._last else max(0.0, target - (now - self._last))
        if sleep_for > 0:
            time.sleep(sleep_for)
        self._last = time.monotonic()
        return sleep_for


# ---------------------------------------------------------------------------
# 1. BaoStock connectivity test
# ---------------------------------------------------------------------------
def test_baostock() -> dict[str, Any]:
    result: dict[str, Any] = {"provider": "baostock", "tests": []}
    try:
        import baostock as bs

        # --- Test 1: basic login ---
        login = bs.login()
        result["tests"].append({
            "label": "login",
            "ok": login.error_code == "0",
            "error_code": login.error_code,
            "error_msg": login.error_msg,
        })

        # --- Test 2: single query history_k_data_plus ---
        rs = bs.query_history_k_data_plus(
            "sz.300308",
            "date,code,open,high,low,close,volume,amount",
            start_date="2026-06-01",
            end_date="2026-06-19",
            frequency="d",
            adjustflag="3",
        )
        rows = []
        while rs.error_code == "0" and rs.next():
            rows.append(dict(zip(rs.fields, rs.get_row_data())))
        result["tests"].append({
            "label": "query_history_k_data_plus",
            "ok": rs.error_code == "0",
            "error_code": rs.error_code,
            "error_msg": rs.error_msg,
            "rows_returned": len(rows),
        })

        # --- Test 3: profit data ---
        rs2 = bs.query_profit_data(code="sz.300308", year=2025, quarter=4)
        rows2 = []
        while rs2.error_code == "0" and rs2.next():
            rows2.append(dict(zip(rs2.fields, rs2.get_row_data())))
        result["tests"].append({
            "label": "query_profit_data",
            "ok": rs2.error_code == "0",
            "error_code": rs2.error_code,
            "error_msg": rs2.error_msg,
            "rows_returned": len(rows2),
        })

        # --- Test 4: login/logout cycle x5 to check stability ---
        cycles = []
        for i in range(5):
            t0 = time.monotonic()
            l = bs.login()
            ok = l.error_code == "0"
            bs.logout()
            elapsed = time.monotonic() - t0
            cycles.append({"cycle": i + 1, "ok": ok, "elapsed_ms": round(elapsed * 1000, 1)})
        result["tests"].append({
            "label": "login_logout_stability",
            "cycles": cycles,
            "ok": all(c["ok"] for c in cycles),
        })

        bs.logout()
        result["overall_ok"] = all(t.get("ok", False) for t in result["tests"])

    except Exception as exc:
        result["exception"] = {"type": type(exc).__name__, "message": str(exc)}
        result["overall_ok"] = False

    return result


# ---------------------------------------------------------------------------
# 2. AKShare multiple endpoint tests
# ---------------------------------------------------------------------------
def test_akshare(rate_limiter: RateLimiter) -> dict[str, Any]:
    result: dict[str, Any] = {"provider": "akshare", "version": None, "tests": []}
    try:
        import akshare as ak

        result["version"] = getattr(ak, "__version__", "unknown")
    except Exception as exc:
        result["tests"].append({
            "label": "import",
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        })
        result["overall_ok"] = False
        return result

    # Each test waits before calling
    tests: list[dict[str, Any]] = []

    # --- Test A: stock_zh_a_hist (Eastmoney push2his) ---
    limiter = RateLimiter(min_seconds=rate_limiter.min_seconds, jitter=rate_limiter.jitter)
    label = "stock_zh_a_hist (Eastmoney push2his)"
    rate_limiter.wait()
    try:
        df = ak.stock_zh_a_hist(symbol="300308", period="daily", start_date="20260601", end_date="20260619", adjust="qfq")
        tests.append({"label": label, "ok": True, "rows": len(df), "tail": df.tail(2).to_dict(orient="records")})
    except Exception as exc:
        tests.append({"label": label, "ok": False, "error_type": type(exc).__name__, "message": str(exc)[:300]})

    # --- Test B: stock_zh_a_daily (Eastmoney new API alternative) ---
    rate_limiter.wait()
    label = "stock_zh_a_daily (Eastmoney alternative)"
    try:
        df = ak.stock_zh_a_daily(symbol="sz300308", adjust="qfq")
        filtered = df[df["date"] >= "2026-06-01"]
        tests.append({"label": label, "ok": True, "rows": len(filtered), "tail": filtered.tail(2).to_dict(orient="records")})
    except Exception as exc:
        tests.append({"label": label, "ok": False, "error_type": type(exc).__name__, "message": str(exc)[:300]})

    # --- Test C: sina daily bar ---
    rate_limiter.wait()
    label = "stock_zh_a_daily_sina"
    try:
        df = ak.stock_zh_a_daily_sina(symbol="sh000001")
        tests.append({"label": label, "ok": True, "rows": len(df), "tail": df.tail(2).to_dict(orient="records")})
    except Exception as exc:
        tests.append({"label": label, "ok": False, "error_type": type(exc).__name__, "message": str(exc)[:300]})

    # --- Test D: Tencent daily bar ---
    rate_limiter.wait()
    label = "stock_zh_a_daily_tencent"
    try:
        df = ak.stock_zh_a_daily_tencent(symbol="sz300308")
        filtered = df[df["date"] >= "2026-06-01"] if "date" in df.columns else df.tail(5)
        tests.append({"label": label, "ok": True, "rows": len(filtered), "tail": filtered.tail(2).to_dict(orient="records")})
    except Exception as exc:
        tests.append({"label": label, "ok": False, "error_type": type(exc).__name__, "message": str(exc)[:300]})

    # --- Test E: netease daily bar ---
    rate_limiter.wait()
    label = "stock_zh_a_daily_netease"
    try:
        df = ak.stock_zh_a_daily_netease(symbol="sz300308")
        filtered = df[df["date"] >= "2026-06-01"] if "date" in df.columns else df.tail(5)
        tests.append({"label": label, "ok": True, "rows": len(filtered), "tail": filtered.tail(2).to_dict(orient="records")})
    except Exception as exc:
        tests.append({"label": label, "ok": False, "error_type": type(exc).__name__, "message": str(exc)[:300]})

    # --- Test F: financial summary ---
    rate_limiter.wait()
    label = "stock_financial_analysis_indicator"
    try:
        df = ak.stock_financial_analysis_indicator(symbol="300308", start_year="2025")
        tests.append({"label": label, "ok": True, "rows": len(df), "columns": list(df.columns[:8])})
    except Exception as exc:
        tests.append({"label": label, "ok": False, "error_type": type(exc).__name__, "message": str(exc)[:300]})

    # --- Test G: fund flow individual ---
    rate_limiter.wait()
    label = "stock_individual_fund_flow"
    try:
        df = ak.stock_individual_fund_flow(stock="300308", market="sh")
        tests.append({"label": label, "ok": True, "rows": len(df), "tail": df.tail(2).to_dict(orient="records")})
    except Exception as exc:
        tests.append({"label": label, "ok": False, "error_type": type(exc).__name__, "message": str(exc)[:300]})

    # --- Test H: stock info ---
    rate_limiter.wait()
    label = "stock_info_a_code_name"
    try:
        df = ak.stock_info_a_code_name()
        row = df[df["code"] == "300308"]
        tests.append({"label": label, "ok": True, "total_rows": len(df), "sample": row.to_dict(orient="records")})
    except Exception as exc:
        tests.append({"label": label, "ok": False, "error_type": type(exc).__name__, "message": str(exc)[:300]})

    result["tests"] = tests
    result["overall_ok"] = any(t.get("ok", False) for t in tests)
    return result


# ---------------------------------------------------------------------------
# 3. Guosen API TLS diagnosis
# ---------------------------------------------------------------------------
def test_guosen() -> dict[str, Any]:
    result: dict[str, Any] = {"provider": "guosen", "tests": []}

    # --- Test A: raw curl to health endpoint ---
    health_tests = [
        {
            "label": "curl_health_no_proxy",
            "cmd": ["curl.exe", "-I", "-k", "--noproxy", "*", "--connect-timeout", "15", "--max-time", "30",
                    "https://dgzt.guosen.com.cn/skills"],
        },
        {
            "label": "curl_health_with_proxy",
            "cmd": ["curl.exe", "-I", "-k", "--connect-timeout", "15", "--max-time", "30",
                    "https://dgzt.guosen.com.cn/skills"],
        },
        {
            "label": "curl_health_tls12",
            "cmd": ["curl.exe", "-I", "-k", "--tlsv1.2", "--noproxy", "*", "--connect-timeout", "15", "--max-time", "30",
                    "https://dgzt.guosen.com.cn/skills"],
        },
        {
            "label": "curl_health_tls13",
            "cmd": ["curl.exe", "-I", "-k", "--tlsv1.3", "--noproxy", "*", "--connect-timeout", "15", "--max-time", "30",
                    "https://dgzt.guosen.com.cn/skills"],
        },
        {
            "label": "curl_health_ssl_no_verify",
            "cmd": ["curl.exe", "-I", "-k", "--noproxy", "*", "-E", "/dev/null", "--connect-timeout", "15", "--max-time", "30",
                    "https://dgzt.guosen.com.cn/skills"],
        },
    ]
    for test in health_tests:
        t0 = time.monotonic()
        try:
            cp = subprocess.run(test["cmd"], capture_output=True, text=True, timeout=40, encoding="utf-8", errors="ignore")
            elapsed = time.monotonic() - t0
            result["tests"].append({
                "label": test["label"],
                "ok": cp.returncode == 0,
                "returncode": cp.returncode,
                "elapsed_ms": round(elapsed * 1000),
                "stderr_snippet": cp.stderr[:200] if cp.stderr else None,
                "stdout_snippet": cp.stdout[:200] if cp.stdout else None,
            })
        except Exception as exc:
            result["tests"].append({
                "label": test["label"],
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            })

    # --- Test B: Python requests with urllib directly (no curl) ---
    rate_limiter = RateLimiter(min_seconds=5, jitter=2)
    rate_limiter.wait()
    test = {"label": "python_requests_guosen"}
    try:
        import requests

        for env_key in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
            v = os.environ.get(env_key)
            test[f"env_{env_key}"] = v[:80] + "..." if v and len(v) > 80 else v

        resp = requests.get(
            "https://dgzt.guosen.com.cn/skills",
            timeout=30,
            verify=False,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        test["ok"] = True
        test["status_code"] = resp.status_code
        test["elapsed_ms"] = 0
    except Exception as exc:
        test["ok"] = False
        test["error_type"] = type(exc).__name__
        test["message"] = str(exc)[:400]

    result["tests"].append(test)

    # --- Test C: try with each key ---
    load_dotenv()
    for key_env in GUOSEN_KEY_ENVS:
        api_key = os.environ.get(key_env)
        if not api_key:
            result["tests"].append({"label": f"guosen_key_{key_env}", "ok": False, "error": "not_in_env"})
            continue
        rate_limiter.wait()
        params = {
            "softName": "goldsun_skills",
            "apiKey": api_key,
            "skillName": "gs-stock-market-query",
            "code": "300308",
            "setCode": "0",
            "target": "0",
        }
        url = f"{GUOSEN_BASE_URL}/gsnews/market/agentbot/queryCombHQ/1.0?{urlencode(params)}"
        try:
            import requests

            resp = requests.get(url, timeout=30, verify=False, headers={"User-Agent": "Mozilla/5.0"})
            try:
                data = resp.json()
                if isinstance(data, dict) and not data.get("error"):
                    result["tests"].append({
                        "label": f"guosen_api_{key_env}",
                        "ok": True,
                        "key_env": key_env,
                        "status_code": resp.status_code,
                        "response_keys": list(data.keys())[:10],
                    })
                else:
                    result["tests"].append({
                        "label": f"guosen_api_{key_env}",
                        "ok": False,
                        "key_env": key_env,
                        "status_code": resp.status_code,
                        "api_error": data.get("error"),
                        "response_keys": list(data.keys())[:10],
                    })
            except json.JSONDecodeError:
                result["tests"].append({
                    "label": f"guosen_api_{key_env}",
                    "ok": False,
                    "key_env": key_env,
                    "status_code": resp.status_code,
                    "raw_snippet": resp.text[:200],
                })
        except Exception as exc:
            result["tests"].append({
                "label": f"guosen_api_{key_env}",
                "ok": False,
                "key_env": key_env,
                "error_type": type(exc).__name__,
                "message": str(exc)[:300],
            })

    result["overall_ok"] = any(t.get("ok", False) for t in result["tests"])
    return result


# ---------------------------------------------------------------------------
# 4. Network / proxy diagnostics
# ---------------------------------------------------------------------------
def test_network_env() -> dict[str, Any]:
    result: dict[str, Any] = {"label": "network_env"}
    proxy_keys = ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "NO_PROXY", "no_proxy", "ALL_PROXY"]
    for k in proxy_keys:
        v = os.environ.get(k)
        if v:
            result[k] = v[:80] + "..." if len(v) > 80 else v
    # curl version
    try:
        cp = subprocess.run(["curl.exe", "--version"], capture_output=True, text=True, timeout=10)
        result["curl_version"] = cp.stdout.split("\n")[0]
    except Exception as exc:
        result["curl_version_error"] = str(exc)
    # python version
    result["python_version"] = sys.version
    # requests version
    try:
        import requests
        result["requests_version"] = requests.__version__
    except Exception as exc:
        result["requests_version_error"] = str(exc)
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    load_dotenv()

    report: dict[str, Any] = {
        "run_at": ts(),
        "python": sys.version,
    }

    # 1. Network env
    print(f"[{ts()}] Testing network environment...")
    report["network_env"] = test_network_env()

    # 2. BaoStock
    print(f"[{ts()}] Testing BaoStock...")
    report["baostock"] = test_baostock()
    print(f"  BaoStock overall_ok={report['baostock'].get('overall_ok')}")

    # 3. AKShare
    limiter = RateLimiter(min_seconds=8.0, jitter=4.0)
    print(f"[{ts()}] Testing AKShare (will take ~80 seconds due to rate limiting)...")
    report["akshare"] = test_akshare(limiter)
    ok_count = sum(1 for t in report["akshare"].get("tests", []) if t.get("ok"))
    total = len(report["akshare"].get("tests", []))
    print(f"  AKShare: {ok_count}/{total} endpoints OK")

    # 4. Guosen
    print(f"[{ts()}] Testing Guosen API (TLS diagnostics)...")
    report["guosen"] = test_guosen()
    ok_count = sum(1 for t in report["guosen"].get("tests", []) if t.get("ok"))
    total = len(report["guosen"].get("tests", []))
    print(f"  Guosen: {ok_count}/{total} tests OK")

    # Save raw report
    save_json(OUT_DIR / "full_connectivity_diagnostic.json", report)

    # Build summary
    summary: dict[str, Any] = {
        "run_at": ts(),
        "baostock": {
            "usable": report["baostock"].get("overall_ok", False),
            "notes": [],
        },
        "akshare": {
            "usable_endpoints": [],
            "unusable_endpoints": [],
            "notes": [],
        },
        "guosen": {
            "usable": False,
            "notes": [],
            "root_cause": None,
        },
    }

    # Parse BaoStock
    if report["baostock"].get("overall_ok"):
        summary["baostock"]["notes"].append("All BaoStock tests passed; use as primary daily kline source.")
    else:
        for t in report["baostock"].get("tests", []):
            if not t.get("ok"):
                summary["baostock"]["notes"].append(f"FAIL: {t.get('label')} -> {t.get('error_code', '?')} {t.get('error_msg', '')}")

    # Parse AKShare
    for t in report["akshare"].get("tests", []):
        if t.get("label") == "import":
            continue
        entry = {"label": t["label"], "ok": t.get("ok", False)}
        if t.get("ok"):
            entry["rows"] = t.get("rows", "?")
            summary["akshare"]["usable_endpoints"].append(entry)
        else:
            entry["error"] = t.get("error_type", "?") + ": " + t.get("message", "")[:120]
            summary["akshare"]["unusable_endpoints"].append(entry)

    # Parse Guosen
    guosen_tests = report["guosen"].get("tests", [])
    curl_health = [t for t in guosen_tests if "curl_health" in t.get("label", "")]
    guosen_api = [t for t in guosen_tests if "guosen_api" in t.get("label", "")]

    if guosen_api and any(t.get("ok") for t in guosen_api):
        summary["guosen"]["usable"] = True
        summary["guosen"]["notes"].append("At least one API key returned valid data via requests.")
    elif curl_health and any(t.get("ok") for t in curl_health):
        summary["guosen"]["usable"] = True
        summary["guosen"]["notes"].append("Curl reached endpoint; use curl backend.")
    else:
        failed_curl = [t for t in curl_health if not t.get("ok")]
        if failed_curl:
            sample = failed_curl[0]
            summary["guosen"]["root_cause"] = {
                "symptom": "TLS/SSL handshake failure",
                "returncode": sample.get("returncode"),
                "stderr": sample.get("stderr_snippet"),
            }
            if "Schannel" in sample.get("stderr_snippet", "") or "SEC_E" in sample.get("stderr_snippet", ""):
                summary["guosen"]["notes"].append("Windows Schannel credential store issue; likely proxy MITM cert not trusted by curl.")
            elif "Connection refused" in sample.get("stderr_snippet", ""):
                summary["guosen"]["notes"].append("Connection refused; check if dgzt.guosen.com.cn is accessible.")
            else:
                summary["guosen"]["notes"].append(f"Unknown TLS failure: {sample.get('stderr_snippet', '')[:100]}")

    save_json(OUT_DIR / "connectivity_summary.json", summary)
    print(f"\n[{ts()}] All tests done. Results:")
    print(f"  BaoStock: {'OK' if summary['baostock']['usable'] else 'FAIL'}")
    print(f"  AKShare usable endpoints: {len(summary['akshare']['usable_endpoints'])}/{len(summary['akshare']['usable_endpoints']) + len(summary['akshare']['unusable_endpoints'])}")
    print(f"  Guosen: {'OK' if summary['guosen']['usable'] else 'FAIL'} - {summary['guosen']['root_cause']}")
    print(f"\nSaved to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
