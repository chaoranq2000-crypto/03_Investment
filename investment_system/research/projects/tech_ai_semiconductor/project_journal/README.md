# Project Journal

This directory is the collaboration log system for `tech_ai_semiconductor`.
It records project setup, migration, audits, handoffs, and cross-session
coordination. It is not a source of truth for formal research claims.

Reusable journal rules, templates, and initialization logic now live in the
global Codex skill `C:\Users\Q\.codex\skills\project-journal`. This directory
keeps only the current project's journal instance, indexes, logs, and archives.

## Directory Roles

- `项目日志总索引.md` is the lightweight catalog for listing and selecting logs without reading log bodies.
- `INDEX.md` records the journal system state, active logs, and archive batches.
- `LOG_CONTROL.md` defines how the user controls reading and writing logs.
- `CHANGELOG.md` records project-setup and workflow changes in chronological order.
- `archive/` stores immutable snapshots of legacy seed documents, plans, audits, and setup records.
- `sessions/` stores one working log per Codex session or focused workstream.
- `handoffs/` stores short handoff notes when work is paused, split, or delegated.
- `decisions/` stores lightweight project-building decisions.
- `templates/` stores copy-ready templates for session logs, handoffs, and decisions.

## Rules

1. Let the user control journal access. If the user gives no logging instruction, default to no journal reads and no journal writes.
2. If the user says `不读日志` or `不写日志`, follow that instruction for the task.
3. If the user wants to choose a log, read only `项目日志总索引.md` first and do not read deeper logs until a log is selected.
4. For multi-session continuation without an explicit choice, do not read logs automatically; list likely candidates only after the user asks `只列日志` or `读日志菜单`.
5. Do not put secrets, API tokens, local proxy credentials, or raw private config in this directory.
6. Do not treat archived seed documents as evidence or formal research sources.
7. Keep formal research outputs out of `project_journal/`; use the project gates for formal publishing.
8. Prefer one primary log per conversation/thread. Append updates to the same log instead of creating several logs.
9. Use separate handoff, decision, or archive files only when the user asks or when the record must be reused outside the conversation.
10. Prefer one focused section per workstream inside the conversation log so parallel tasks do not overwrite each other.
11. Update `项目日志总索引.md` when adding a new active session, handoff, decision, or archive batch.
12. Archive by copy/snapshot first. Do not move live files unless a later task explicitly requests it.
13. Do not create or maintain a separate log menu file; use `项目日志总索引.md` for log selection.
14. For reuse in another project, use the global `$project-journal` skill instead of copying this project directory.

## Naming

- Session log: `sessions/YYYY-MM-DD-<中文语义主题>.md`
- Handoff: `handoffs/YYYY-MM-DD-<中文语义主题>.md`
- Decision: `decisions/YYYY-MM-DD-<中文语义主题>.md`
- Archive batch: `archive/YYYY-MM-DD-<scope>/`

Prefer Chinese semantic names, so the user can say things like
`读日志 项目日志系统搭建与规则合并` or `读日志 当前Tushare主数据源计划`.
