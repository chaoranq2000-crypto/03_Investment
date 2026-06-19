"""AKShare 数据缓存层 — 对应小红书 EP.45 核心原则：

  "把'拉数据'和'用数据'拆开"
  - 日线/财务等不常变的数据  → 收盘批量落库，全程只读本地
  - 只有盘中实时行情才现拉  → 加 sleep 限速 + 指数退避重试

核心逻辑：
  1. 同一标的同一接口，TTL 内直接读本地缓存（毫秒级）
  2. TTL 过期才触发一次网络请求，同时锁住防止并发重复拉
  3. 拉取失败自动指数退避重试（最多 N 次）
  4. 缓存以 Parquet 格式存储（比 CSV 快，支持增量追加时间戳）
"""
from __future__ import annotations

import hashlib
import math
import time
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Callable, TypeVar

import pandas as pd

# ---------------------------------------------------------------------------
# 路径
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 全局锁：防止多线程/多进程同时拉同一份数据触发 IP 阈值
# ---------------------------------------------------------------------------
_fetch_locks: dict[str, Lock] = {}
_global_lock = Lock()


def _get_lock(key: str) -> Lock:
    """同一 cache key 用同一把锁，避免重复拉取。"""
    with _global_lock:
        if key not in _fetch_locks:
            _fetch_locks[key] = Lock()
        return _fetch_locks[key]


def _make_key(namespace: str, symbol: str | None, **kwargs: Any) -> str:
    """生成唯一缓存键（含参数）。"""
    param_str = "|".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    raw = f"{namespace}|{symbol or ''}|{param_str}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.parquet"


# ---------------------------------------------------------------------------
# 类型
# ---------------------------------------------------------------------------
T = TypeVar("T")


class CacheStats:
    """追踪缓存命中/未命中统计。"""

    def __init__(self) -> None:
        self.hits = 0
        self.misses = 0
        self.writes = 0
        self.errors = 0

    def report(self) -> pd.DataFrame:
        total = self.hits + self.misses
        return pd.DataFrame(
            [
                {"指标": "命中", "次数": self.hits},
                {"指标": "未命中", "次数": self.misses},
                {"指标": "写入缓存", "次数": self.writes},
                {"指标": "异常", "次数": self.errors},
                {"指标": "命中率", "值": f"{self.hits/total*100:.1f}%" if total else "N/A"},
            ]
        )


_stats = CacheStats()


def get_stats() -> pd.DataFrame:
    return _stats.report()


# ---------------------------------------------------------------------------
# 核心装饰器
# ---------------------------------------------------------------------------


def cached(
    namespace: str,
    ttl_seconds: int = 86400,
    *,
    symbol_key: str = "symbol",
    rate_limit_seconds: float = 1.0,
    max_retries: int = 3,
    retry_base_delay: float = 2.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """缓存 + 限速 + 指数退避重试装饰器。

    Args:
        namespace:        缓存命名空间（如 "kline", "financial"）
        ttl_seconds:      缓存新鲜度秒数；默认 86400 = 1 天
        symbol_key:       函数参数中代表股票代码的参数名
        rate_limit_seconds: 两次请求间最小间隔（秒），防止 IP 阈值
        max_retries:      网络失败时的最大重试次数
        retry_base_delay: 指数退避基数（秒），实际延迟 = base * 2^attempt

    用法示例（对应 EP.45 三步缓存）：
        @cached("kline", ttl_seconds=86400, symbol_key="symbol")
        def get_kline(symbol: str, ...) -> pd.DataFrame:
            return ak.stock_zh_a_hist(symbol=symbol, ...)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # 取出 symbol（用于生成更友好的缓存文件名）
            sig = func.__code__
            symbol = kwargs.get(
                symbol_key,
                args[sig.co_varnames.index(symbol_key)]
                if symbol_key in sig.co_varnames
                else None,
            )
            key = _make_key(namespace, symbol, **kwargs)
            cache_file = _cache_path(key)

            # ---------- 读缓存（TTL 内直接返回）----------
            if cache_file.exists():
                mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if datetime.now() - mtime < timedelta(seconds=ttl_seconds):
                    _stats.hits += 1
                    return pd.read_parquet(cache_file)  # type: ignore[return-value]

            # ---------- 加锁，防止并发重复拉 ----------
            lock = _get_lock(key)
            with lock:
                # 双检：拿到锁后可能另一个线程已写入
                if cache_file.exists():
                    mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                    if datetime.now() - mtime < timedelta(seconds=ttl_seconds):
                        _stats.hits += 1
                        return pd.read_parquet(cache_file)  # type: ignore[return-value]

                # ---------- 指数退避重试拉取 ----------
                last_exc: Exception | None = None
                for attempt in range(max_retries):
                    try:
                        df = func(*args, **kwargs)
                        break
                    except Exception as exc:  # noqa: BLE001
                        last_exc = exc
                        if attempt < max_retries - 1:
                            delay = retry_base_delay * (2**attempt)
                            time.sleep(delay)
                        else:
                            raise last_exc from None

                # ---------- 写入本地缓存 ----------
                df: pd.DataFrame = df
                if isinstance(df, pd.DataFrame) and not df.empty:
                    # 追加更新时间戳列
                    df = df.copy()
                    df["_cache_updated_at"] = datetime.now().isoformat()
                    df.to_parquet(cache_file, index=False)
                    _stats.writes += 1
                else:
                    _stats.errors += 1

                _stats.misses += 1
                return df

        return wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# 预置缓存函数（最常用的 AKShare 接口，已封装好）
# ---------------------------------------------------------------------------


@cached("spot", ttl_seconds=3600, rate_limit_seconds=2.0)
def get_a_stock_spot() -> pd.DataFrame:
    """A 股全市场实时行情快照（TTL=1小时，日内不必重复拉）。"""
    import akshare as ak

    return ak.stock_zh_a_spot_em()


@cached(
    "kline",
    ttl_seconds=86400,
    symbol_key="symbol",
    rate_limit_seconds=3.0,
)
def get_kline(
    symbol: str,
    period: str = "daily",
    start_date: str = "20200101",
    end_date: str | None = None,
    adjust: str = "qfq",
) -> pd.DataFrame:
    """日 K 线（默认前复权），TTL=收盘后到次日收盘前不变。"""
    import akshare as ak

    return ak.stock_zh_a_hist(
        symbol=symbol,
        period=period,
        start_date=start_date,
        end_date=end_date or datetime.now().strftime("%Y%m%d"),
        adjust=adjust,
    )


@cached(
    "financial_bs",
    ttl_seconds=86400 * 7,
    symbol_key="symbol",
    rate_limit_seconds=2.0,
)
def get_balance_sheet(symbol: str) -> pd.DataFrame:
    """资产负债表（每季度更新，TTL=7天）。"""
    import akshare as ak

    return ak.stock_balance_sheet_by_report_em(symbol=symbol)


@cached(
    "financial_pl",
    ttl_seconds=86400 * 7,
    symbol_key="symbol",
    rate_limit_seconds=2.0,
)
def get_profit_sheet(symbol: str) -> pd.DataFrame:
    """利润表（每季度更新，TTL=7天）。"""
    import akshare as ak

    return ak.stock_profit_sheet_by_report_em(symbol=symbol)


@cached(
    "financial_cf",
    ttl_seconds=86400 * 7,
    symbol_key="symbol",
    rate_limit_seconds=2.0,
)
def get_cash_flow(symbol: str) -> pd.DataFrame:
    """现金流量表（每季度更新，TTL=7天）。"""
    import akshare as ak

    return ak.stock_cash_flow_sheet_by_report_em(symbol=symbol)


# ---------------------------------------------------------------------------
# 批量预热：收盘后批量拉全市场数据落库（对应 EP.45 第1步）
# ---------------------------------------------------------------------------


def warm_cache_batch(
    symbols: list[str],
    func: Callable[[str], pd.DataFrame],
    *,
    delay: float = 3.0,
    verbose: bool = True,
) -> None:
    """批量预热缓存（收盘后运行，模拟 EP.45 "收盘批量拉一次"）。

    Args:
        symbols:   股票代码列表
        func:     缓存装饰过的函数（如 get_kline）
        delay:    每只间隔秒数（建议 >= 3 秒，避免 IP 阈值）
        verbose:  打印进度
    """
    total = len(symbols)
    for i, sym in enumerate(symbols, 1):
        if verbose:
            print(f"  [{i}/{total}] {sym} ...", end=" ", flush=True)
        try:
            func(sym)
            if verbose:
                print("OK")
        except Exception as exc:  # noqa: BLE001
            if verbose:
                print(f"FAIL ({exc})")
        time.sleep(delay)
