# 投资体系架构

## 1. 分层设计

### A. 数据层

职责：

- 从 AKShare、国信 API、PDF 公告、手工资料中获取数据。
- 使用本地缓存，避免重复请求和限频。
- 区分原始数据、加工数据、最终分析结果。

建议目录：

```text
investment_system/data/
├── raw/          # 原始接口返回、PDF 文本、OCR 文本
├── cache/        # Parquet/pickle 缓存
├── processed/    # 清洗后的指标表
└── snapshots/    # 每日快照
```

现有对应：

- `akshare_lab/data/cache`
- `Investment Research/tmp/research_data`
- `Investment Research/tmp/pdfs`

### B. 数据管道层

职责：

- 拉取行情、K 线、财务、资金流、公告文本。
- 做字段标准化、单位转换、代码市场映射。
- 输出统一格式的数据表。

建议目录：

```text
investment_system/pipelines/
├── ingest/       # 数据拉取
├── transform/    # 清洗标准化
├── features/     # 指标加工
└── quality/      # 数据质量检查
```

### C. 研究层

职责：

- 管理行业、公司、主题、催化剂、竞争格局。
- 保存研究笔记、证据链、估值假设和报告。

建议目录：

```text
investment_system/research/
├── companies/
├── sectors/
├── themes/
├── evidence/
└── templates/
```

现有对应：

- `Investment Research/reports`
- `Investment Research/tmp/research_data`

### D. 策略与评分层

职责：

- 建立股票池。
- 根据财务质量、成长性、估值、趋势、资金流、催化剂打分。
- 输出候选名单和调仓建议。

建议模块：

```text
score = quality + growth + valuation + momentum + catalyst - risk_penalty
```

### E. 实时操作决策层

职责：

- 把研究结论和实时行情转化为可执行的买入、卖出、加仓、减仓、持有、观察动作。
- 管理盘中触发条件、价格区间、仓位规则、失效条件和执行记录。
- 区分“研究观点”和“操作指令”，避免因为看好公司而自动买入。

建议目录：

```text
investment_system/decisions/
├── candidates/     # 候选操作
├── active/         # 当前有效决策
├── executed/       # 已执行操作
├── invalidated/    # 已失效决策
└── templates/      # 决策卡模板
```

实时操作决策卡建议字段：

| 字段 | 说明 |
|---|---|
| 标的 | 股票代码、名称、市场 |
| 决策类型 | 买入、加仓、减仓、清仓、持有、观察 |
| 实时触发条件 | 价格、涨跌幅、成交量、资金流、板块联动、公告事件 |
| 研究依据 | 关联报告、财务指标、估值假设、催化剂 |
| 操作区间 | 计划买入/卖出价格区间 |
| 仓位规则 | 初始仓位、最大仓位、加减仓条件 |
| 失效条件 | 哪些变化会取消当前操作 |
| 风险点 | 估值、流动性、事件、市场环境风险 |
| 执行记录 | 实际成交、仓位变化、执行原因 |
| 复盘日期 | 计划回看日期 |

### F. 组合与风控层

职责：

- 记录持仓、观察池、交易计划。
- 管理仓位上限、止损规则、事件风险和复盘。

建议目录：

```text
investment_system/portfolio/
├── watchlist/
├── positions/
├── trades/
└── reviews/
```

组合层记录最终持仓和交易结果；实时操作决策层记录为什么此刻要动、动多少、什么条件下撤销。

## 2. 数据刷新频率

| 数据类型 | 建议频率 | 来源 | 说明 |
|---|---:|---|---|
| 日 K 线 | 每日收盘后 | AKShare/国信 API | 不要盘中反复拉 |
| 财务三表 | 每周或公告后 | AKShare/国信 API | 季报年报低频 |
| 实时行情 | 盘中按需 | AKShare/国信 API | 单点请求，加限速重试 |
| 资金流 | 每日收盘后 | 国信 API | 可作为短线辅助 |
| 公告/PDF | 事件触发 | PDF/MinerU | 进入证据库 |
| 研究报告 | 人工触发 | 本地 Markdown | 进入研究层 |
| 操作决策 | 盘中/收盘后 | 行情+研究+风控 | 进入实时操作决策层 |

## 3. 环境原则

- `akshare_lab` 普通任务用 `akshare_lab/.venv/Scripts/python.exe`。
- `Investment Research` 普通任务用 `Investment Research/.venv/Scripts/python.exe`。
- PDF MinerU 解析按 `Investment Research/AGENTS.md`，调用外部 MinerU 环境。
- 新建通用脚本前，优先判断它属于数据层、研究层、实时操作决策层还是组合层，避免继续散落在 `tmp`。
