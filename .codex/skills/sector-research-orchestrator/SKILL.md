---
name: sector-research-orchestrator
description: Orchestrates A-share sector and sub-theme research workflows in C:\Projects\03_Investment, especially AI算力硬件 and 半导体国产替代. Use when the user asks to run板块调研, 科技主线调研, P0/P1/P2批量调研, 补全缺失数据, 标准化调研流程, or generate/update structured research cards, cross-theme comparison tables, company financial valuation tables, source indexes, missing-data logs, and quality checks.
---

# Sector Research Orchestrator

Use this as the top-level board/sector research workflow. It coordinates lower-level project skills and pipeline scripts; it should not duplicate their logic.

## Required Context

Read these only when needed:

- `references/workflow.md` for the step-by-step lower-skill orchestration.
- `references/quality_gates.md` for acceptance checks.
- `references/data_sources.md` for data-source priority, fallback, and rate limits.
- `investment_system/docs/research_workflow.md` for the project-level research-grade workflow.
- `investment_system/docs/report_quality_standard.md` when the user asks for a report that is ready for investment reading.

## Workflow

1. Inspect current outputs, docs, registry rows, and pipeline scripts.
2. Invoke `market-data-router` for K-line, quotes, turnover, relative-strength inputs.
3. Invoke `financial-data-router` for revenue, profit, margins, EPS, PE, PS inputs.
4. Invoke `evidence-miner` for annual-report, announcement, IR, Q&A, policy, and broker evidence.
5. Invoke `forecast-normalizer` for 2026E/2027E forecasts, PE, PEG, institution counts.
6. Invoke `research-writer` to generate cards, total tables, logs, and source indexes.
7. Invoke `quality-auditor` to run cleanup, pipeline-grade validation, research-grade validation, conflict checks, and stale-data checks.
8. Loop back to the failing lower skill if validation fails.

## Commands

Use the project Conda runtime:

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\pipelines\run_research.py --sub-theme "高速光模块" --skip-guosen
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\pipelines\cleanup_outputs.py
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\pipelines\validate_outputs.py --sub-theme "高速光模块"
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\pipelines\validate_outputs.py --sub-theme "高速光模块" --grade research
```

## Rules

- Preserve source traceability: source name, date, URL/path, excerpt, supported fields, confidence.
- Prefer company reports, announcements, IR records, and exchange Q&A over media or summaries.
- Use the configured client entry points: BaoStock/Tencent/AKShare through `research_client.py`, and Tushare through `investment_system/pipelines/tushare_client.py`; do not use disabled Guosen skills or hand-roll duplicate request logic.
- If all configured interfaces fail for a required field, invoke web evidence mining and record a verifiable local cache path or webpage URL.
- AKShare and other public web sources must be rate-limited and small-batch only.
- Do not write API keys into reports, logs, or generated CSV/Markdown.
- Do not batch-delete files or directories.
- Keep final CSV/Markdown as generated artifacts; durable manual evidence belongs in `investment_system/research/evidence/`.
