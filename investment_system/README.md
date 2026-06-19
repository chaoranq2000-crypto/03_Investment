# 投资体系总控

这个目录是 `C:\Projects\03_Investment` 的统一投资体系入口，用来把现有的 AKShare 实验、国信接口投研、PDF 资料、报告产出和组合管理整合到同一套流程里。

当前原则：

- 不移动、不删除现有项目文件。
- 先建立统一规范，再逐步迁移已有脚本和报告。
- 数据采集、研究分析、策略筛选、实时操作决策、组合管理、风险复盘分层管理。
- 普通 Python 任务优先使用所在子项目的本地 `.venv`。
- 如需删除文件，只允许一次删除一个明确路径的文件，禁止批量删除目录或文件。

## 现有项目定位

| 目录 | 当前用途 | 建议角色 |
|---|---|---|
| `akshare_lab` | AKShare 缓存实验室 | 数据采集与本地缓存层 |
| `Investment Research` | 投研报告、国信 API 数据、PDF 资料 | 研究分析与报告产出层 |
| `AKSHARE` | 小红书截图与 OCR 资料 | 方法论资料归档 |
| `investment_system` | 新增总控目录 | 统一架构、流程、配置和迁移入口 |

## 目标体系

```text
数据源 -> 数据缓存 -> 指标加工 -> 股票池/策略筛选 -> 个股研究 -> 估值与风险 -> 实时操作决策 -> 执行跟踪 -> 复盘归档
```

## 推荐阅读顺序

1. `docs/architecture.md`
2. `docs/operating_workflow.md`
3. `docs/migration_plan.md`
4. `config/universe.example.yaml`
