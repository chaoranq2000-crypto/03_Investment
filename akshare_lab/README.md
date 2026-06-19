# AKShare 工作流实验室

基于 AKShare + 批处理缓存策略的 A 股数据工作流，参考小红书 EP.45 @moonipulate 的"AI 投研踩坑实录"整理。

## 核心原则（EP.45）

> **把"拉数据"和"用数据"拆开**

| 维度 | 实时硬拉 ❌ | 批处理 + 缓存 ✅ |
|------|-------------|------------------|
| 限频风险 | 极高，必触发 IP 阈值 | 几乎为零 |
| 速度 | 每次等网络，慢 | 读本地，毫秒级 |
| 稳定性 | 源抖动就崩 | 离线也能跑策略 |
| 适用 | 仅盘中实时行情 | 日线 / 财务 / 不常变数据 |

## 项目结构

```
akshare_lab/
├── .venv/                   # Python 虚拟环境（已配置好）
├── src/
│   ├── akshare_utils.py     # 中文字体 + 路径 + 保存工具
│   └── cache.py             # 缓存层（TTL + 限速 + 指数退避重试）
├── examples/
│   ├── 01_a_stock_spot.py   # 全市场快照（TTL=1小时）
│   ├── 02_kline_chart.py    # 单股 K 线 + 中文化画图
│   ├── 03_financials.py     # 财务三大表（TTL=7天）
│   ├── 04_simple_screen.py   # 选股模板（全程读本地缓存）
│   └── _verify.py            # 环境验证脚本（不需要网络）
├── data/
│   ├── cache/                # Parquet 缓存文件（按 TTL 自动生成）
│   └── *.csv                 # 输出数据
├── outputs/                  # 图表输出
├── requirements.txt
└── README.md
```

## 快速开始

### 1. 激活虚拟环境

```powershell
# 方式 A：直接用 .venv 里的 python.exe
& "C:\Projects\03_Investment\akshare_lab\.venv\Scripts\python.exe" examples/04_simple_screen.py

# 方式 B：激活后运行
& "C:\Projects\03_Investment\akshare_lab\.venv\Scripts\Activate.ps1"
python examples/04_simple_screen.py
```

### 2. 验证环境（不需要网络）

```bash
python examples/_verify.py
```

预期输出：
```
=== Font detection ===
Active font: C:\Windows\Fonts\msyh.ttc   # 微软雅黑，Windows 10+ 自带

=== Cache key uniqueness: PASS
```

### 3. 运行示例

```bash
# 示例 1：全市场快照（首次从网络，后续读本地）
python examples/01_a_stock_spot.py

# 示例 2：K 线图（TTL=1天）
python examples/02_kline_chart.py 600519

# 示例 3：财务三大表（TTL=7天）
python examples/03_financials.py 600519

# 示例 4：选股筛选（全程读缓存，无网络请求）
python examples/04_simple_screen.py
```

## 缓存策略详解

### TTL 设计

| 数据类型 | 接口 | TTL | 说明 |
|----------|------|-----|------|
| 全市场快照 | `stock_zh_a_spot_em` | 1 小时 | 日内重复运行不拉网络 |
| 日 K 线 | `stock_zh_a_hist` | 1 天 | 收盘后到次日收盘前不变 |
| 财务报表 | `stock_xxx_by_report_em` | 7 天 | 季报/年报按季度更新 |
| 实时行情 | `stock_zh_a_spot` | 5 分钟 | 盘中才需要真正实时 |

### 限速机制

- **请求间隔**：同一接口每次请求间隔 ≥ 1 秒
- **指数退避**：网络失败时等待 `2^attempt` 秒后重试（最多 3 次）
- **并发锁**：同一标的用同一把锁，防止多线程重复拉取

### 预热缓存（收盘后运行）

```python
from src.cache import warm_cache_batch, get_kline

# 批量预热：收盘后一次性落库
symbols = ["600519", "000858", "601318"]
warm_cache_batch(symbols, get_kline, delay=3.0)
```

## 中文字体说明

已解决 Windows 10+ 缺少 `simfang.ttf` 的问题，按以下优先级自动选择：

1. `C:\Windows\Fonts\msyh.ttc` — **微软雅黑（已找到）**
2. `C:\Windows\Fonts\simsun.ttc` — 宋体
3. `C:\Windows\Fonts\Deng.ttf` — 等线（Win10 1809+ 自带）

如果均未找到，运行 `python -c "from src.akshare_utils import list_installed_cn_fonts; print(list_installed_cn_fonts())"` 查看可用字体。

## 依赖说明

所有依赖已在虚拟环境中配置好：

- `akshare >= 1.15.0` — 财经数据接口
- `pandas >= 2.2.0` — 数据处理
- `matplotlib >= 3.8.0` — 可视化
- `pyarrow` — Parquet 格式（缓存存储）
- `rapidocr_onnxruntime` — 可选 OCR（用于图片文字识别）

## 故障排查

### 网络请求失败 / IP 限频

这是 AKShare 的正常行为，不是 bug。解决方式：
1. 等待几分钟后再试（IP 解封需要时间）
2. 优先使用缓存（TTL 内不会重复请求）
3. 使用 `warm_cache_batch` 在收盘后批量预热

### 中文字体显示为方框

运行验证脚本确认字体路径：
```bash
python examples/_verify.py
```
如果显示 `(未找到)`，说明字体文件缺失，可从 [Google Noto Fonts](https://fonts.google.com/specimen/Noto+Sans+SC) 下载安装。

### 缓存文件损坏

删除 `data/cache/` 目录，缓存会自动重新生成：
```powershell
Remove-Item "C:\Projects\03_Investment\akshare_lab\data\cache" -Recurse -Force
```
