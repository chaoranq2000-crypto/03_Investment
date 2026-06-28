# 数据管道目录

这里用于放新建的数据采集、清洗、指标加工和质量检查脚本。

Phase 6 迁移状态：

- `.codex/skills/*/scripts/cli.py` 是当前推荐的人机操作入口。
- `investment_system/pipelines/sector_research/*.py` 中多数文件已经是兼容 wrapper，保留用于旧命令和内部调用过渡。
- `run_research.py`、`evidence_overrides.py`、`tushare_client.py`、`sector_research/load_project.py` 仍保留 legacy/compatibility 职责，不在当前阶段删除。
- wrapper 保留/废弃清单见 `investment_system/research/projects/tech_ai_semiconductor/audits/legacy_wrapper_retention_plan_phase6.md`。

优先方向：

1. AKShare 缓存层标准化。
2. Tushare、BaoStock、AKShare 数据标准化。
3. 统一证券代码、市场、日期、单位字段。
4. 输出 Parquet 或 CSV，供研究和组合模块读取。


