"""示例 03：A 股财务三大表（资产负债表/利润表/现金流量表）。

缓存 TTL=7天（财务数据按季度更新，无需每日重复拉取）。

运行：
    python examples/03_financials.py 600519
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cache import get_balance_sheet, get_cash_flow, get_profit_sheet  # noqa: E402
from akshare_utils import OUTPUT_DIR  # noqa: E402


def main() -> None:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "600519"
    print(f"查询标的: {symbol}  财务数据缓存 TTL=7天（日内不会重复拉网络）\n")

    print(f"[1/3] 资产负债表（TTL=7天）...")
    bs = get_balance_sheet(symbol)
    print(f"    -> {len(bs):,} 行，最新报告期: {bs.iloc[0]['报告日期']}")

    print(f"[2/3] 利润表（TTL=7天）...")
    pl = get_profit_sheet(symbol)
    print(f"    -> {len(pl):,} 行，最新报告期: {pl.iloc[0]['报告日期']}")

    print(f"[3/3] 现金流量表（TTL=7天）...")
    cf = get_cash_flow(symbol)
    print(f"    -> {len(cf):,} 行，最新报告期: {cf.iloc[0]['报告日期']}")

    print(f"\n输出目录: {OUTPUT_DIR.resolve()}")
    print(f"BS 缓存文件: data/cache/financial_bs_*.parquet")


if __name__ == "__main__":
    main()
