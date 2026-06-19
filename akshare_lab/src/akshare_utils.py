"""AKShare 工作流共享工具：统一字体、网络与文件路径。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import matplotlib
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd

# ---------------------------------------------------------------------------
# 路径
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# 中文字体：解决 Windows 10+ 缺少 simfang.ttf / simhei.ttf 的问题
# ---------------------------------------------------------------------------
_CN_FONT_CANDIDATES = [
    # 优先使用 Windows 自带 / Office 自带的开源中文字体
    r"C:\Windows\Fonts\msyh.ttc",        # 微软雅黑
    r"C:\Windows\Fonts\msyh.ttf",
    r"C:\Windows\Fonts\msyhl.ttc",       # 微软雅黑 Light
    r"C:\Windows\Fonts\simhei.ttf",      # 黑体
    r"C:\Windows\Fonts\simsun.ttc",      # 宋体
    r"C:\Windows\Fonts\simkai.ttf",      # 楷体
    r"C:\Windows\Fonts\Deng.ttf",        # 等线 (Win10 1809+)
    r"C:\Windows\Fonts\NotoSansCJK-Regular.ttc",  # Google Noto（如已装）
    "/System/Library/Fonts/PingFang.ttc",         # macOS
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Linux
]


def configure_chinese_font(force: bool = False) -> str | None:
    """配置 matplotlib 让中文正常显示。

    返回最终使用的字体文件路径；找不到时返回 None。
    Windows 10/11 至少自带 msyh.ttc；simfang.ttf 在新版系统已移除。
    """
    matplotlib.rcParams["axes.unicode_minus"] = False  # 负号显示

    for path in _CN_FONT_CANDIDATES:
        if path and os.path.exists(path):
            try:
                fm.fontManager.addfont(path)
                font_name = fm.FontProperties(fname=path).get_name()
                matplotlib.rcParams["font.family"] = font_name
                matplotlib.rcParams["font.sans-serif"] = [
                    font_name,
                    "DejaVu Sans",
                ]
                if force:
                    # 清缓存强制重建
                    cache_dir = matplotlib.get_cachedir()
                    for f in Path(cache_dir).glob("fontlist*.json"):
                        try:
                            f.unlink()
                        except OSError:
                            pass
                return path
            except Exception as exc:  # noqa: BLE001
                print(f"[font] {path} 加载失败: {exc}", file=sys.stderr)

    print(
        "[font] 未找到任何可用的中文字体，请在 C:\\Windows\\Fonts\\ 安装 msyh.ttc "
        "或 NotoSansCJK，并重新运行。",
        file=sys.stderr,
    )
    return None


def list_installed_cn_fonts() -> pd.DataFrame:
    """列出本机已安装的中文字体（按文件路径）。"""
    rows = []
    for path in _CN_FONT_CANDIDATES:
        if path and os.path.exists(path):
            try:
                name = fm.FontProperties(fname=path).get_name()
            except Exception:
                name = "(无法读取)"
            rows.append({"path": path, "font_name": name, "exists": True})
    return pd.DataFrame(rows)


def save_csv(df: pd.DataFrame, name: str, *, index: bool = False) -> Path:
    """把 DataFrame 存到 data/ 下，避免污染工作区根目录。"""
    path = DATA_DIR / f"{name}.csv"
    df.to_csv(path, index=index, encoding="utf-8-sig")
    return path


def save_figure(fig: plt.Figure, name: str) -> Path:
    path = OUTPUT_DIR / f"{name}.png"
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


# 模块被 import 时立刻尝试一次配置
configure_chinese_font()
