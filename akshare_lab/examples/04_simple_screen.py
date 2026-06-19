"""示例 04：简单选股 + 评估模板（全面使用缓存，对应 EP.45 完整流程）。

策略：
  1) 全市场快照读缓存（TTL=1小时）
  2) 筛出：市值 50~500亿 / 市盈率 TTM 在 0.1~30 / 今日涨幅为正
  3) 按综合得分排序取前 20

EP.45 关键：
  - 运行策略全程只读本地缓存，不触发任何网络请求（毫秒级）
  - 只有缓存 TTL 过期时才补拉（收盘批量）

运行：
    python examples/04_simple_screen.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd

from cache import get_a_stock_spot, get_stats  # noqa: E402
from akshare_utils import save_csv  # noqa: E402


def screen(df: pd.DataFrame) -> pd.DataFrame:
    """评估函数：对全市场快照进行选股过滤，返回排名结果。"""
    # 列名映射（东方财富实时数据字段）
    rename_map = {
        "代码": "code",
        "名称": "name",
        "最新价": "price",
        "涨跌幅": "pct_chg",
        "涨跌额": "chg",
        "成交量": "volume",
        "成交额": "turnover",
        "振幅": "amplitude",
        "最高": "high",
        "最低": "low",
        "今开": "open",
        "昨收": "prev_close",
        "市盈率-动态": "pe_ttm",
        "市净率": "pb",
        "总市值": "mcap",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    for col in ["price", "pct_chg", "pe_ttm", "pb", "mcap"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    result = df[
        df["mcap"].between(5e9, 5e10)
        & df["pe_ttm"].between(0.1, 30)
        & (df["pct_chg"] > 0)
        & df.get("name", pd.Series(dtype=str)).str.fullmatch(r"[\u4e00-\u9fa5A-Za-z]+", na=False)
    ].copy()

    result["score"] = -result["pe_ttm"] * 0.1 + result["pct_chg"] * 0.5
    return (
        result.sort_values("score", ascending=False)
        .head(20)
        .reset_index(drop=True)
    )


def main() -> None:
    print("[1/4] 通过缓存读取 A 股全市场快照（TTL=1小时，日内只拉一次）...")
    spot = get_a_stock_spot()
    print(f"    -> 共 {len(spot):,} 只标的")

    print("[2/4] 选股过滤（全程只读内存，无网络请求）...")
    picks = screen(spot)
    print(f"    -> 命中 {len(picks)} 只")
    display_cols = ["code", "name", "price", "pct_chg", "pe_ttm", "mcap", "score"]
    print(picks[display_cols].to_string(index=False))

    print("[3/4] 保存结果...")
    out = save_csv(picks, "screen_result")
    print(f"    -> {out}")

    print("[4/4] 缓存统计（展示命中率）:")
    print(get_stats().to_string(index=False))


if __name__ == "__main__":
    main()
