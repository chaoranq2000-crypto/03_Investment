# Project Journal Index

Project: `tech_ai_semiconductor`
Created: 2026-06-29
Purpose: multi-session project-building coordination.

## Current State

- Active runtime surface: `investment_system/core/`
- Human-facing workflow entry points: `.codex/skills/*/scripts/cli.py`
- Main project config: `investment_system/research/projects/tech_ai_semiconductor/`
- Formal output root: `C:/Projects/03_Investment/科技主线调研输出`
- Journal status: initialized with a bootstrap archive snapshot on 2026-06-29; root `skill_module_refactor_plan.md` live duplicate retired to archive on 2026-06-30; changed audit snapshots refreshed on 2026-06-30; archived audit originals retired from live `audits/` on 2026-06-30.
- Journal access is user-controlled through `LOG_CONTROL.md`.
- Default behavior is no journal reads and no journal writes unless the user explicitly asks.
- Lightweight log discovery uses `项目日志总索引.md`; agents should not read full log bodies just to find available logs.
- Reusable journal workflow now lives in the global skill: `C:/Users/Q/.codex/skills/project-journal/`.

## User-Controlled Log Access

- To decide whether logs should be read or written, use `LOG_CONTROL.md`.
- To choose which log to read, use `项目日志总索引.md`.
- Short commands supported by the journal convention:
  - `不读日志`
  - `不写日志`
  - `只列日志`
  - `读日志菜单`
  - `读日志 <中文日志名>`
  - `写日志`

## Active Logs

Latest setup session:

- `sessions/2026-06-29-项目日志系统搭建与规则合并.md`

Start new work from:

- `templates/session_log_template.md`
- `templates/handoff_template.md`
- `templates/decision_record_template.md`

## Handoffs

- `handoffs/2026-06-30-workflow-stage-contract重构交接.md`
  - Status: current
  - Purpose: GitHub / 网页端 GPT 协作交接，说明 `workflow_stages.yaml` schema 收敛和 `workflow-stage-contract` 审计新增情况。

## Decisions

- No separate decision log is active. Decisions should be appended to the primary session log unless the user asks for `写决策`.

## Archive Batches

- `archive/2026-06-29-bootstrap-docs/`
  - Scope: existing seed documents, project plans, audit/change records, and selected project state manifests.
  - Method: copied snapshot; original live files were not moved.
  - Manifest: `archive/2026-06-29-bootstrap-docs/archive_manifest.csv`
  - Note: `plans/skill_module_refactor_plan.md` is now the retained copy after the root live duplicate was retired on 2026-06-30.
  - Note: archived live `audits/` originals were deleted one by one on 2026-06-30 after user confirmation.
- `archive/2026-06-30-audits-refresh/`
  - Scope: current `audits/` files whose hashes changed after the bootstrap archive.
  - Method: copied snapshot; original live audit files were not moved.
  - Manifest: `archive/2026-06-30-audits-refresh/archive_manifest.csv`
  - Note: unchanged audit files remain covered by the 2026-06-29 bootstrap archive; archived live originals were deleted one by one on 2026-06-30 after user confirmation.

## Reading Rule For New Sessions

If the user gives no explicit logging instruction:

1. Do not read journal logs.
2. Do not read `项目日志总索引.md` or full log bodies.
3. Do not write session, handoff, decision, changelog, or archive files.
4. Use live config and validation commands to verify anything that may have changed.

If the user gives an explicit logging instruction:

1. `只列日志` or `读日志菜单`: read only `项目日志总索引.md`.
2. `读日志 <中文日志名>`: resolve the path from `项目日志总索引.md`, then read only the selected item.
3. `写日志`: write or append one primary conversation log unless the user asks for a separate handoff, decision, or archive.

## Boundaries

- `project_journal/` is coordination memory, not formal evidence.
- `project_journal/` is the current project's journal instance; the reusable system and templates belong to the global `project-journal` skill.
- `archive/` preserves historical context, not active runtime ownership.
- Current project behavior should still be verified against live config and validation commands.
