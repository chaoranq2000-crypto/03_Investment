# 投资体系总控

这个目录是 `C:\Projects\03_Investment` 的统一投资体系入口，用来把数据源配置、研究资料、报告产出、实时操作决策和组合管理整合到同一套流程里。

当前原则：

- 不移动、不删除现有项目文件。
- 先建立统一规范，再逐步迁移已有脚本和报告。
- 数据采集、研究分析、策略筛选、实时操作决策、组合管理、风险复盘分层管理。
- 普通 Python 任务统一使用项目根目录 Conda 环境 `.conda/investment-system`。
- 如需删除文件，只允许一次删除一个明确路径的文件，禁止批量删除目录或文件。

## 现有项目定位

| 目录 | 当前用途 | 建议角色 |
|---|---|---|
| `.conda/investment-system` | 项目根目录 Conda 环境 | 统一 Python 运行环境 |
| `investment_system` | 投资体系总控目录 | 架构、流程、配置、数据管道和决策入口 |
| `A股科技前两主线调研文件包` | 当前调研资料包 | 研究资料、模板和报告输入 |

## 目标体系

```text
数据源 -> 数据缓存 -> 指标加工 -> 股票池/策略筛选 -> 个股研究 -> 估值与风险 -> 实时操作决策 -> 执行跟踪 -> 复盘归档
```

## 推荐阅读顺序

1. `docs/architecture.md`
2. `docs/operating_workflow.md`
3. `docs/migration_plan.md`
4. `docs/data_source_configuration.md`
5. `config/data_sources.example.toml`
6. `config/universe.example.yaml`
