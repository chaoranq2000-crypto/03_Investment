---
name: sector-research-orchestrator
description: Orchestrates A-share sector and sub-theme research workflows in C:\Projects\03_Investment, especially AI算力硬件 and 半导体国产替代. Use when the user asks to run板块调研, 科技主线调研, P0/P1/P2批量调研, 补全缺失数据, 标准化调研流程, or generate/update structured research cards, cross-theme comparison tables, company financial valuation tables, source indexes, missing-data logs, and quality checks.
---

# Sector Research Orchestrator

Use this skill as the top-level workflow. Do not replace the lower-level data tools; call the project pipeline scripts and validate outputs.

## Required Context

Read these only when needed:

- `references/workflow.md` for the execution flow and command order.
- `references/quality_gates.md` for acceptance checks.
- `references/data_sources.md` for data-source priority, fallback, and rate limits.

## Workflow

1. Inspect current outputs and pipeline scripts before changing anything.
2. Run or update the unified project scripts under `investment_system/pipelines/`.
3. Put curated company/industry evidence under `investment_system/research/evidence/`; do not treat final output files as source data.
4. Keep raw data under `investment_system/data/raw/` and processed data under `investment_system/data/processed/`.
5. Generate final deliverables under `科技主线调研输出/`.
6. Run `investment_system/pipelines/cleanup_outputs.py`.
7. Run `investment_system/pipelines/validate_outputs.py --sub-theme <细分方向>`.
8. Report remaining gaps explicitly. Do not claim all fields are filled if any CSV field still contains `缺失`.

## Commands

Use the project Conda runtime:

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\pipelines\run_research.py --sub-theme "高速光模块" --skip-guosen
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\pipelines\cleanup_outputs.py
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\pipelines\validate_outputs.py --sub-theme "高速光模块"
```

## Rules

- Preserve source traceability: source name, date, URL/path, excerpt, supported fields, confidence.
- Prefer company reports, announcements, IR records, and exchange Q&A over media or summaries.
- Use BaoStock/Tencent/Guosen/AKShare through `research_client.py`; do not hand-roll duplicate request logic.
- AKShare and other public web sources must be rate-limited and small-batch only.
- Do not write API keys into reports, logs, or generated CSV/Markdown.
- Do not batch-delete files or directories.
