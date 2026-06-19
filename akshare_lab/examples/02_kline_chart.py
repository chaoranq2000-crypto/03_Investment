"""示例 02：单只股票历史 K 线 + 中文化画图（带缓存）。

缓存 TTL=1天（收盘后落库，次日直接读本地，不再触发网络）。
解决之前截图里 matplotlib 找不到 simfang.ttf 的问题：
  自动按优先级查找 msyh.ttc / simhei.ttf / Deng.ttf 等 Windows 10+ 自带字体。

运行：
    python examples/02_kline_chart.py 600519
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import matplotlib.pyplot as plt
import pandas as pd

from akshare_utils import configure_chinese_font, save_figure  # noqa: E402
from cache import get_kline  # noqa: E402


def main() -> None:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "600519"

    print(f"[1/4] 配置中文字体（不再依赖已弃用的 simfang.ttf）...")
    font_path = configure_chinese_font(force=False)
    print(f"    -> 使用字体: {font_path or '(未找到，中文将显示为方框)'}")

    print(f"[2/4] 通过缓存层拉取 {symbol} 日 K 线（TTL=1天）...")
    df = get_kline(symbol=symbol, start_date="20240101")
    print(f"    -> 拿到 {len(df):,} 行，最新日期: {df.iloc[-1]['日期']}")
    if df.empty:
        print("未取到数据，请检查股票代码。")
        return

    print(f"[3/4] 画图...")
    fig, ax = plt.subplots(figsize=(11, 5))
    df["日期_dt"] = pd.to_datetime(df["日期"])
    ax.plot(df["日期_dt"], df["收盘"], linewidth=1.3, label="收盘价(前复权)")
    ax.set_title(f"{symbol} 历史收盘价", fontsize=14)
    ax.set_xlabel("日期")
    ax.set_ylabel("价格 (元)")
    ax.grid(alpha=0.3)
    ax.legend()

    fig_path = save_figure(fig, f"kline_{symbol}")
    print(f"[4/4] 图表已保存: {fig_path}")


if __name__ == "__main__":
    main()
