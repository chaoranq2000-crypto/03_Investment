# 投资体系总控

这个目录是 `C:\Projects\03_Investment` 的统一投资体系入口，用来把数据源配置、研究资料、报告产出、实时操作决策和组合管理整合到同一套流程里。

当前可执行流程以 `.codex/skills/*/scripts/cli.py` 为主；可复用实现位于 `investment_system/core/`。资料型数据源手册放在 `investment_system/docs/data_sources/`，不作为 workflow skill 激活。`investment_system/pipelines/` 已退役，不再作为源码或文档边界保留。

## 工作流事实源边界

`tech_ai_semiconductor` 的阶段顺序、CLI 路由、默认写入模式、正式输出边界、人工确认要求和 warning-only 规则，只以 `investment_system/research/projects/tech_ai_semiconductor/workflow_stages.yaml` 为准。

本 README 只做导航，不复述完整阶段链。`AGENTS.md` 只保留仓库级护栏；各 `.codex/skills/*/SKILL.md` 只描述单个 skill 的职责和入口；`sector-research-orchestrator` 负责读取项目阶段策略并调度对应 skill。

当前原则：

- 不移动、不删除正式研究输出，除非任务明确要求。
- 先建立统一规范，再逐步迁移已有脚本和报告。
- 数据采集、研究分析、策略筛选、实时操作决策、组合管理、风险复盘分层管理。
- 普通 Python 任务统一使用项目根目录 Conda 环境 `.conda/investment-system`。
- 如需删除文件，只允许一次删除一个明确路径的文件，禁止批量删除目录或文件。

## 现有项目定位

| 目录 | 当前用途 | 建议角色 |
|---|---|---|
| `.conda/investment-system` | 项目根目录 Conda 环境 | 统一 Python 运行环境 |
| `investment_system` | 投资体系总控目录 | 可复用引擎、配置、数据、证据和质量门 |
| `investment_system/docs/data_sources` | 数据源资料、接口手册、外部参考包 | 只作参考；需要时将最小可验证逻辑迁移到对应 workflow skill |
| `.codex/skills` | Codex 操作规程 | 单 skill 职责、入口和契约引用 |
| `科技主线调研输出` | 正式生成物 | 只通过 gate 后的发布流程写入 |

## 目标体系

```text
数据源 -> 数据缓存 -> 指标加工 -> 股票池/策略筛选 -> 个股研究 -> 估值与风险 -> 实时操作决策 -> 执行跟踪 -> 复盘归档
```

## 推荐阅读顺序

1. `investment_system/research/projects/tech_ai_semiconductor/workflow_stages.yaml`
2. `.codex/skills/sector-research-orchestrator/SKILL.md`
3. `.codex/skills/sector-research-orchestrator/references/workflow.md`
4. `.codex/skills/sector-research-orchestrator/references/quality_gates.md`
5. `.codex/skills/sector-research-orchestrator/references/data_sources.md`
6. `.codex/skills/sector-research-orchestrator/references/architecture.md`
7. `.codex/skills/quality-auditor/references/research_grade_standard.md`
8. `investment_system/config/data_sources.example.toml`
9. `investment_system/docs/data_sources/README.md`

## 当前推荐入口

```powershell
# Run one configured stage. Stage names and write policy live in workflow_stages.yaml.
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\sector-research-orchestrator\scripts\cli.py run-stage --project tech_ai_semiconductor --sector-id <canonical_sector_id> --stage <stage_name>

# Project-level scope check shortcut.
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\sector-research-orchestrator\scripts\cli.py scope-check --project tech_ai_semiconductor
```
