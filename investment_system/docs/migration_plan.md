# 迁移计划

迁移目标是逐步形成统一体系，而不是一次性大搬家。所有步骤默认不删除旧文件。

## 阶段 1：建立总控规范

状态：已开始。

任务：

- 创建 `investment_system` 总控目录。
- 明确现有目录角色。
- 写入体系架构、日常流程和迁移计划。

## 阶段 2：整理现有资产清单

建议生成以下清单：

- 已有报告清单
- 已有数据文件清单
- 已有脚本清单
- 已有 API/skill 清单
- 已有虚拟环境与依赖清单

输出：

```text
investment_system/docs/inventory.md
```

## 阶段 3：统一数据接口

优先处理：

- `investment_system/pipelines` 中新的 AKShare、BaoStock、国信 API 管道。
- `investment_system/config/data_sources.example.toml` 中的数据源优先级、限速和缓存策略。

目标：

- 把 AKShare 和国信 API 都纳入统一数据层。
- 保留各自可运行入口，不强行合并。
- 新脚本优先写到 `investment_system/pipelines`。

## 阶段 4：统一研究产出

建议：

- 当前研究资料以 `A股科技前两主线调研文件包` 为输入。
- 新报告统一沉淀到 `investment_system/research` 或后续正式报告目录。
- 在 `investment_system/research/templates` 建立统一报告模板。

## 阶段 5：建立股票池和评分系统

建议先实现最小可用版本：

- 股票池配置：`config/universe.yaml`
- 指标输入：财务、估值、趋势、资金流
- 输出：候选名单、评分、理由、风险

## 阶段 6：建立实时操作决策层

建立：

- 实时操作决策卡模板
- 盘前候选操作池
- 盘中实时行情与技术面触发条件表
- 已执行操作记录
- 失效/取消操作记录

目标：

- 研究报告给出观点。
- 实时操作决策卡结合实时股价、技术面和仓位规则给出可执行动作。
- 组合记录保存最终持仓与交易结果。

## 阶段 7：组合与复盘

建立：

- 观察池
- 持仓表
- 交易计划
- 每日复盘
- 每周复盘

## 禁止事项

- 禁止批量删除文件或目录。
- 禁止使用 `Remove-Item -Recurse`、`rm -rf`、`rmdir /s` 等命令。
- 不要把 API Key 写入报告、日志或公开文件。
- 不要复制整个外部 MinerU 环境到当前项目。
