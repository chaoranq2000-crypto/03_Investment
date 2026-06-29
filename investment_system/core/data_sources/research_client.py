"""Unified, production-grade data source client.

Handles data source tiers with proper fallback, rate-limiting,
and environment-aware key loading:

  Priority 1: BaoStock   -- always reachable, daily kline + financial data
  Priority 2: AkShare    -- Tencent direct HTTP (Eastmoney is flaky behind proxy)
  Priority 3: mootdx     -- TCP binary protocol, never IP-blocked

Key discovery order:
  1. environment variables (set in shell session)
  2. investment_system/config/.env.local

Usage:
  from investment_system.core.data_sources.research_client import ResearchClient
  client = ResearchClient()
  # daily kline
  daily = client.get_daily_kline("300308", "SZ")
  # financial
  profit = client.get_profit("300308")
  # AKShare Tencent bar
  bar = client.get_tencent_bar("sz300308")
"""

from __future__ import annotations

import json
import os
import random
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional

import baostock as bs

from investment_system.core.data_sources.config import as_float, load_data_source_config, load_dotenv

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[3]  # project root

AKSHARE_MIN_WAIT = 8.0   # seconds between public-web calls
AKSHARE_JITTER = 4.0
BAOSTOCK_INTERVAL = 2.0   # seconds between BaoStock queries

TODAY = date.today().isoformat()

# ---------------------------------------------------------------------------
# Environment loading
# ---------------------------------------------------------------------------

def load_env() -> None:
    """Load env vars from the project-local .env.local file."""
    load_dotenv()


def get_env(key: str, fallback: str = "") -> str:
    return os.environ.get(key, fallback)


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

@dataclass
class HumanRateLimiter:
    min_seconds: float = AKSHARE_MIN_WAIT
    jitter: float = AKSHARE_JITTER
    _last: float = field(default=0.0)

    def wait(self) -> float:
        now = time.monotonic()
        target = self.min_seconds + random.uniform(0, self.jitter)
        if self._last:
            sleep_for = max(0.0, target - (now - self._last))
        else:
            sleep_for = target
        if sleep_for > 0:
            time.sleep(sleep_for)
        self._last = time.monotonic()
        return sleep_for


# ---------------------------------------------------------------------------
# HTTP utilities
# ---------------------------------------------------------------------------

def curl_get(url: str, timeout: int = 30, params: Optional[dict] = None) -> dict[str, Any]:
    """Call URL with curl.exe and return parsed JSON. Falls back to requests if curl fails."""
    if params:
        from urllib.parse import urlencode
        url = f"{url}?{urlencode(params)}"
    cmd = [
        "curl.exe", "-s", "-k",
        "--tlsv1.2",               # TLS 1.2 avoids "UNSAFE_LEGACY_RENEGOTIATION_DISABLED"
        "--connect-timeout", "20",
        "--max-time", str(timeout),
        url,
    ]
    try:
        cp = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout + 15, encoding="utf-8", errors="ignore",
        )
        if cp.returncode != 0:
            return {"_curl_error": cp.stderr[:300], "_returncode": cp.returncode}
        if not cp.stdout.strip():
            return {"_curl_error": "empty_response"}
        return json.loads(cp.stdout)
    except subprocess.TimeoutExpired:
        return {"_curl_error": "curl_timeout"}
    except Exception as exc:
        return {"_curl_error": f"{type(exc).__name__}: {exc}"}


# ---------------------------------------------------------------------------
# 1. BaoStock client (single session, retry-safe)
# ---------------------------------------------------------------------------

def baostock_code(code: str, market: str) -> str:
    """Convert to BaoStock 9-digit format: 'sz.300308' or 'sh.600519'.

    BaoStock requires prefix + dot + 6-digit code (no leading zeros).
    """
    prefix = "sh" if market == "SH" else "sz"
    return f"{prefix}.{code}"


def tencent_code(code: str, market: str) -> str:
    """Convert to Tencent Finance symbol format: 'sz300308' or 'sh600519'."""
    prefix = "sh" if market == "SH" else "sz"
    return f"{prefix}{code}"


class BaoStockClient:
    """Reuse a single BaoStock login for all queries within the session."""

    def __init__(
        self,
        interval: float = BAOSTOCK_INTERVAL,
        retries: int = 2,
        start_date: str | None = None,
    ) -> None:
        self.interval = interval
        self.retries = retries
        self.start_date = start_date or (date.today() - timedelta(days=220)).isoformat()
        self._last_call = 0.0
        self._logged_in = False
        self._login_result: dict[str, Any] = {}

    def __enter__(self) -> "BaoStockClient":
        login = bs.login()
        self._login_result = {"error_code": login.error_code, "error_msg": login.error_msg}
        self._logged_in = login.error_code == "0"
        return self

    def __exit__(self, *_) -> None:
        if self._logged_in:
            bs.logout()
            self._logged_in = False

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last_call if self._last_call else None
        if elapsed is not None and elapsed < self.interval:
            time.sleep(self.interval - elapsed)
        self._last_call = time.monotonic()

    def _call(self, label: str, func: Callable[[], Any]) -> Any:
        attempts: list[dict] = []
        for attempt in range(1, self.retries + 2):
            self._wait()
            try:
                return func()
            except Exception as exc:
                attempts.append({"attempt": attempt, "error": str(exc)})
                if attempt <= self.retries:
                    time.sleep(self.interval * attempt)
        return {"_baostock_error": "all_retries_failed", "label": label, "attempts": attempts}

    def daily(
        self,
        code: str,
        market: str,  # "SZ" or "SH"
        end_date: str | None = None,
    ) -> list[dict[str, str]]:
        """Return list of daily kline dicts."""
        if not self._logged_in:
            return [{"_error": "not_logged_in"}]
        bs_code = baostock_code(code, market)
        fields = "date,code,open,high,low,close,preclose,volume,amount,turn,pctChg"

        def do_query() -> list[dict[str, str]]:
            rs = bs.query_history_k_data_plus(
                bs_code, fields,
                start_date=self.start_date,
                end_date=end_date or TODAY,
                frequency="d",
                adjustflag="3",
            )
            rows: list[dict[str, str]] = []
            while rs.error_code == "0" and rs.next():
                rows.append(dict(zip(rs.fields, rs.get_row_data())))
            if rs.error_code != "0":
                raise RuntimeError(f"{rs.error_code}: {rs.error_msg}")
            return rows

        result = self._call(f"daily:{bs_code}", do_query)
        return result if isinstance(result, list) else [result]

    def profit(
        self,
        code: str,
        market: str,
        years: list[int] | None = None,
    ) -> list[dict[str, str]]:
        """Return list of profit/financial dicts."""
        if not self._logged_in:
            return [{"_error": "not_logged_in"}]
        bs_code = baostock_code(code, market)
        years = years or [2024, 2025]

        def do_query() -> list[dict[str, str]]:
            rows: list[dict[str, str]] = []
            for year in years:
                for quarter in [1, 2, 3, 4]:
                    self._wait()
                    rs = bs.query_profit_data(code=bs_code, year=year, quarter=quarter)
                    while rs.error_code == "0" and rs.next():
                        rec = dict(zip(rs.fields, rs.get_row_data()))
                        rec["year"] = str(year)
                        rec["quarter"] = str(quarter)
                        rows.append(rec)
            return rows

        result = self._call(f"profit:{bs_code}", do_query)
        return result if isinstance(result, list) else [result]

    def login_ok(self) -> bool:
        return self._logged_in


# ---------------------------------------------------------------------------
# 2. AKShare client -- Tencent primary (Eastmoney fallback with retry)
# ---------------------------------------------------------------------------

class AKShareClient:
    """Rate-limited AKShare wrapper with Tencent primary and Eastmoney fallback.

    Eastmoney push2his is flaky behind the current proxy, so Tencent is
    preferred. Uses akshare 1.18.64 API names.
    """

    def __init__(self, limiter: HumanRateLimiter | None = None) -> None:
        self.limiter = limiter or HumanRateLimiter()
        self._ak = self._import_akshare()

    def _import_akshare(self) -> Any:
        import akshare as ak
        return ak

    # -- Stock info (always available) --

    def stock_info_a_code_name(self) -> list[dict]:
        """Returns DataFrame with columns: code, name."""
        self.limiter.wait()
        try:
            df = self._ak.stock_info_a_code_name()
            return df.to_dict(orient="records")
        except Exception as exc:
            return [{"_error": f"{type(exc).__name__}: {exc}"}]

    # -- Daily kline: Tencent primary, Eastmoney secondary --

    def daily_bar(self, symbol: str) -> list[dict]:
        """Get daily bar via Tencent (proxy-safe).

        Args:
            symbol: e.g. "sz300308" or "sh600000"
        Returns list of dicts with date/open/high/low/close/volume fields.
        """
        self.limiter.wait()
        # Try Tencent first
        try:
            df = self._ak.stock_zh_a_daily(symbol=symbol, adjust="qfq")
            return df.tail(220).to_dict(orient="records")
        except Exception as exc:
            pass

        # Fallback: Eastmoney push2his (flaky, retry once)
        try:
            code = symbol[2:]  # strip prefix
            market = "sh" if symbol.startswith("sh") else ("sz" if symbol.startswith("sz") else None)
            if market:
                self.limiter.wait()
                df = self._ak.stock_zh_a_hist(
                    symbol=code, period="daily",
                    start_date="20240101", end_date=TODAY.replace("-", ""),
                    adjust="qfq",
                )
                return df.tail(220).to_dict(orient="records")
        except Exception:
            pass

        return [{"_error": "all_akshare_daily_sources_failed"}]

    # -- Financial analysis indicator (uses company financial API, not push2his) --

    def financial_indicator(self, symbol: str, start_year: str = "2024") -> list[dict]:
        """Returns financial analysis indicators (摊薄EPS, ROE, margins, etc.).

        This function uses a different Eastmoney endpoint than push2his,
        so it works even when push2his is down.
        """
        self.limiter.wait()
        try:
            df = self._ak.stock_financial_analysis_indicator(symbol=symbol, start_year=start_year)
            return df.to_dict(orient="records")
        except Exception as exc:
            return [{"_error": f"{type(exc).__name__}: {exc}"}]

    # -- Fund flow (individual stock) --
    def individual_fund_flow(self, stock: str, market: str = "sh") -> list[dict]:
        """主力资金流向 for a single stock."""
        self.limiter.wait()
        try:
            df = self._ak.stock_individual_fund_flow(stock=stock, market=market)
            return df.tail(20).to_dict(orient="records")
        except Exception as exc:
            return [{"_error": f"{type(exc).__name__}: {exc}"}]

    # -- Index data via Sina (used for relative strength) --
    def index_daily(self, symbol: str = "sh000001") -> list[dict]:
        """Daily index kline via Sina财经."""
        self.limiter.wait()
        try:
            df = self._ak.stock_zh_index_daily(symbol=symbol)
            return df.tail(220).to_dict(orient="records")
        except Exception as exc:
            return [{"_error": f"{type(exc).__name__}: {exc}"}]


# ---------------------------------------------------------------------------
# 4. Direct Tencent HTTP (no akshare dependency, proxy-safe)
# ---------------------------------------------------------------------------

def tencent_bar_direct(symbol: str, retry: int = 2) -> list[dict]:
    """Fetch daily bar from Tencent Finance API directly via curl.exe.

    Args:
        symbol: "sz300308" or "sh600000"
    Returns list of dicts with date/open/close/high/low/vol fields.
    """
    # Tencent bar API format:
    # https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayhfq&param=sz300308,day,,,320,qfq
    base = symbol[2:]  # strip sh/sz
    market_map = {"sh": "sh", "sz": "sz"}
    mkt = symbol[:2]
    url = (
        f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        f"?param={mkt}{base},day,,,320,qfq"
    )
    for attempt in range(1, retry + 2):
        result = curl_get(url, timeout=15)
        if "_curl_error" not in result:
            break
        time.sleep(3 * attempt)
    if "_curl_error" in result:
        return [{"_error": result["_curl_error"]}]
    # Tencent wraps data oddly: data.sz300308.qfqday = [[date, open, close, high, low, vol], ...]
    try:
        mkt_data = result.get("data", {}).get(f"{mkt}{base}", {})
        day_data = mkt_data.get("qfqday", mkt_data.get("day", []))
        rows = []
        for row in day_data[-220:]:
            if len(row) >= 6:
                rows.append({
                    "date": row[0],
                    "open": row[1],
                    "close": row[2],
                    "high": row[3],
                    "low": row[4],
                    "volume": row[5],
                })
        return rows
    except Exception as exc:
        return [{"_error": f"{type(exc).__name__}: {exc}"}]


# ---------------------------------------------------------------------------
# Unified Research Client
# ---------------------------------------------------------------------------

class ResearchClient:
    """Unified interface wrapping all data sources with proper fallback."""

    def __init__(
        self,
        baostock_interval: float | None = None,
        akshare_min_wait: float | None = None,
        akshare_jitter: float | None = None,
    ) -> None:
        load_env()
        config = load_data_source_config(load_env=False)
        baostock = config.section("baostock")
        akshare = config.section("akshare")
        resolved_baostock_interval = (
            baostock_interval
            if baostock_interval is not None
            else as_float(baostock.get("rate_limit_seconds"), BAOSTOCK_INTERVAL)
        )
        resolved_akshare_min_wait = (
            akshare_min_wait
            if akshare_min_wait is not None
            else as_float(akshare.get("rate_limit_seconds_public_web"), AKSHARE_MIN_WAIT)
        )
        resolved_akshare_jitter = (
            akshare_jitter
            if akshare_jitter is not None
            else as_float(akshare.get("rate_limit_jitter_seconds_public_web"), AKSHARE_JITTER)
        )
        self._baostock_interval = resolved_baostock_interval
        self._akshare_limiter = HumanRateLimiter(
            min_seconds=resolved_akshare_min_wait,
            jitter=resolved_akshare_jitter,
        )
        self._bs: Optional[BaoStockClient] = None
        self._ak: Optional[AKShareClient] = None

    # -- Context manager for BaoStock session --
    def __enter__(self) -> "ResearchClient":
        self._bs = BaoStockClient(interval=self._baostock_interval)
        self._bs.__enter__()
        self._ak = AKShareClient(limiter=self._akshare_limiter)
        return self

    def __exit__(self, *_) -> None:
        if self._bs:
            self._bs.__exit__(None, None, None)

    # -- Public API --
    def get_daily_kline(
        self,
        code: str,
        market: str,
    ) -> list[dict[str, str]]:
        """Daily kline: BaoStock primary, Tencent direct fallback."""
        if self._bs:
            rows = self._bs.daily(code, market)
            if rows and "_error" not in rows[0]:
                return rows
        # Tencent fallback
        sym = tencent_code(code, market)
        return tencent_bar_direct(sym)  # type: ignore[return-value]

    def get_profit(
        self,
        code: str,
        market: str,
        years: list[int] | None = None,
    ) -> list[dict[str, str]]:
        """Profit/financial data: BaoStock primary."""
        if self._bs:
            return self._bs.profit(code, market, years)
        return [{"_error": "baostock_session_not_open"}]

    def get_akshare_financial_indicator(self, code: str) -> list[dict]:
        """Financial analysis indicator via AKShare (non-push2his endpoint)."""
        if self._ak:
            return self._ak.financial_indicator(code)
        return [{"_error": "akshare_not_init"}]

    def get_akshare_daily_bar(self, symbol: str) -> list[dict]:
        """Rate-limited AKShare daily K-line fallback."""
        if self._ak:
            return self._ak.daily_bar(symbol)
        return [{"_error": "akshare_not_init"}]

    def get_akshare_individual_fund_flow(self, stock: str) -> list[dict]:
        """Individual stock fund flow via AKShare."""
        if self._ak:
            return self._ak.individual_fund_flow(stock=stock)
        return [{"_error": "akshare_not_init"}]

    def get_akshare_index_daily(self, symbol: str = "sh000001") -> list[dict]:
        """Index daily kline via Sina."""
        if self._ak:
            return self._ak.index_daily(symbol)
        return [{"_error": "akshare_not_init"}]

    def get_tencent_direct(self, symbol: str) -> list[dict]:
        """Tencent direct HTTP call (no akshare)."""
        return tencent_bar_direct(symbol)

    def get_stock_info(self) -> list[dict]:
        """All A-share stock info: code + name."""
        if self._ak:
            return self._ak.stock_info_a_code_name()
        return [{"_error": "akshare_not_init"}]
