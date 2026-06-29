# Project-Building Changelog

This file tracks project setup and workflow-system changes. It does not replace
Git history, audit reports, or formal research logs.

## 2026-06-29

- Created `project_journal/` as the collaboration log system for multi-session and parallel work.
- Added the initial directory model: `archive/`, `sessions/`, `handoffs/`, `decisions/`, and `templates/`.
- Established the first archive batch: `archive/2026-06-29-bootstrap-docs/`.
- Chose snapshot-based archiving so live project references such as `run_manifest.yaml` and `sector_universe.yaml` remain intact.
- Added `project_journal` to the project Markdown scan exclude list so journal archives are not treated as unregistered seed documents.
- Added user-controlled log access through `LOG_CONTROL.md` and `LOG_SELECTOR.md`, including short commands such as `不读日志`, `不写日志`, `只列日志`, and `读日志 <中文日志名>`.
- Added log read/write control rules; these are now consolidated into the primary setup log.
- Renamed active journal session, handoff, and decision records to Chinese semantic filenames.
- Updated `LOG_SELECTOR.md` so Chinese log names are the primary selection keys while English aliases remain supported.
- Added the `one conversation, one log` rule: append updates to a single primary conversation log unless the user explicitly asks for a separate handoff, decision, or archive.
- Consolidated earlier split session/handoff/decision logs into one primary session log: `sessions/2026-06-29-项目日志系统搭建与规则合并.md`.
- Added `项目日志总索引.md` as a lightweight catalog so agents can list and select logs without reading log bodies.
- Changed the default journal policy to no reads and no writes unless the user gives an explicit logging instruction.
- Removed `LOG_SELECTOR.md`; `项目日志总索引.md` is now the single log selection surface.
- Moved the reusable journal workflow into the global skill `C:\Users\Q\.codex\skills\project-journal`; this project folder now serves as an instance only.
