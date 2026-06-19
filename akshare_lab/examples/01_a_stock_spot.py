"""示例 01：A 股全市场快照（带缓存，TTL=1小时）。

对应小红书 EP.45：日内重复运行不会重新拉数据，直接读本地缓存。

运行：
    python examples/01_a_stock_spot.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cache import get_a_stock_spot, get_stats  # noqa: E402


def main() -> None:
    print("[1/3] 通过缓存层拉取 A 股全市场实时快照（首次运行从网络，后续读本地）...")
    df = get_a_stock_spot()
    print(f"    -> 拿到 {len(df):,} 行")

    print("[2/3] 前 10 行：")
    print(df.head(10).to_string(index=False))

    print("[3/3] 缓存统计：")
    print(get_stats().to_string(index=False))


if __name__ == "__main__":
    main()
