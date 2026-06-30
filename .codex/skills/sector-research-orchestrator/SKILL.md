---
name: sector-research-orchestrator
description: Orchestrates A-share sector research workflows in C:\Projects\03_Investment. Use when the user asks to run板块调研, 科技主线调研, P0/P1/P2批量调研, 补全缺失数据, 标准化调研流程, or generate/update structured research cards, cross-theme comparison tables, company financial valuation tables, source indexes, missing-data logs, and quality checks.
---

# Sector Research Orchestrator

Use this as the top-level board/sector research workflow. It coordinates lower-level project skills and shared core helpers; it should not duplicate their logic.

## Required Context

Read these only when needed:

- `references/workflow.md` for the step-by-step lower-skill orchestration.
- `references/quality_gates.md` for acceptance checks.
- `references/data_sources.md` for data-source priority, fallback, and rate limits.
- `references/architecture.md` for the current project-aware engine boundaries and formal-output safety model.
- `../quality-auditor/references/research_grade_standard.md` when the user asks for a report that is ready for investment reading.

## Workflow Authority

Use the skill CLI entry points first. Project-specific stage order, stage CLI routing, default modes, write boundaries, manual-confirmation requirements, publish scope, and warning-only handling are owned by:

- `investment_system/research/projects/<project_id>/workflow_stages.yaml`

This file is the coordinator guide, not a second workflow fact source. It should explain when to use the orchestrator and how to invoke configured stages; it must not restate the full project workflow.

When asked to run or explain the current workflow:

1. Inspect `workflow_stages.yaml` for the current configured stages and write policy.
2. Use `scope-check` before a new phase.
3. Use `run-stage --stage <stage_name>` for configured stages.
4. Loop back to the lower skill named by the failing stage or gate.
5. Do not reintroduce removed pipeline wrappers or broad-runner compatibility modules.

## Commands

Use the project Conda runtime:

```powershell
# Project scope check:
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\sector-research-orchestrator\scripts\cli.py scope-check --project tech_ai_semiconductor

# Run one configured stage. Read workflow_stages.yaml for supported stages and write policy:
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\sector-research-orchestrator\scripts\cli.py run-stage --project tech_ai_semiconductor --sector-id <canonical_sector_id> --stage <stage_name>
```

## Rules

- Preserve source traceability: source name, date, URL/path, excerpt, supported fields, confidence.
- Prefer company reports, announcements, IR records, and exchange Q&A over media or summaries.
- Use the configured client entry points: BaoStock/Tencent/AKShare through `investment_system.core.data_sources.research_client`, and Tushare diagnostics through `market-data-router` or `financial-data-router` `tushare-ping`; do not use disabled Guosen skills or hand-roll duplicate request logic.
- If all configured interfaces fail for a required field, invoke web evidence mining and record a verifiable local cache path or webpage URL.
- AKShare and other public web sources must be rate-limited and small-batch only.
- Do not write API keys into reports, logs, or generated CSV/Markdown.
- Do not batch-delete files or directories.
- Keep final CSV/Markdown as generated artifacts; durable manual evidence belongs in `investment_system/research/evidence/`.
- Do not hand-edit `sector_universe.yaml` evidence bindings when `evidence-miner register` or `register-apply` can do the registration safely.
- Do not treat a candidate as publishable until `candidate_gate` has passed and `publish_gate` has completed its dry-run checks.
