# Log Control

This file defines how a user controls whether project journal files are read or
written. The journal is useful for cross-session continuity, but it should not
take control away from the user.

## User Commands

Use any of these short commands at the start of a task.

| Command | Meaning |
|---|---|
| `不读日志` | Do not read project journal files for this task. Work only from live files and the current request. |
| `不写日志` | Do not create or update project journal files for this task. |
| `只列日志` | Show available logs from `项目日志总索引.md`; do not read log contents yet. |
| `读日志菜单` | Open `项目日志总索引.md` and let the user choose which log to read. |
| `读日志 <中文日志名>` | Resolve the selected item from `项目日志总索引.md`, then read only that one log or document. |
| `写日志` | Create or update the relevant session/handoff/decision log for this task. |
| `写交接` | Write a handoff note only. |
| `写决策` | Write a decision record only. |

## Default Behavior

If the user gives no logging instruction:

1. Do not read project journal files, including indexes.
2. Do not create or update project journal files.
3. Work from the current user request, live repository files, and validation commands.
4. If a task appears to benefit from older logs, name the likely log candidate from prior context if known, but wait for an explicit `读日志 <中文日志名>` or `只列日志` instruction before reading.
5. If the user later asks to write logs, prefer one primary journal file for the conversation/thread. Append updates, decisions, and next steps to that file instead of creating multiple logs.
6. Create a separate handoff, decision, or archive file only when the user explicitly asks (`写交接`, `写决策`, archive/checkpoint).
7. Do not write archive snapshots unless the user explicitly asks to archive or checkpoint.

## Read Levels

| Level | Reads | When to use |
|---|---|---|
| none | no journal files | `不读日志`, quick checks, isolated tasks |
| index | `项目日志总索引.md` only | `只列日志`, `读日志菜单`, user wants to choose |
| targeted | one selected log or archive manifest | explicit `读日志 <中文日志名>` |
| full | `项目日志总索引.md` plus explicitly selected session/handoff/decision/archive files | explicit recovery or handoff request |

## Write Levels

| Level | Writes | When to use |
|---|---|---|
| none | no journal writes | `不写日志`, read-only or small task |
| session | `sessions/YYYY-MM-DD-<中文语义主题>.md` | active workstream tracking |
| handoff | `handoffs/YYYY-MM-DD-<中文语义主题>.md` | pause, split, or next-session transfer |
| decision | `decisions/YYYY-MM-DD-<中文语义主题>.md` | durable project-building decision |
| archive | `archive/YYYY-MM-DD-<中文或英文scope>/` | explicit checkpoint or legacy snapshot |

## One Conversation, One Log

- Default to one primary session log per conversation/thread.
- If the conversation already has a session log, append to it instead of creating a new session log.
- Put small decisions, validation summaries, and next steps inside the same session log.
- Create separate `handoffs/` or `decisions/` files only when the user asks for them or when they need to be reusable outside this conversation.
- If multiple parallel workstreams happen inside one conversation, keep one conversation log with separate sections unless the user asks to split them.
- When unsure, ask before creating another journal file.

## Naming Rules

- Prefer Chinese semantic names for session, handoff, and decision logs.
- Keep the date prefix for sorting: `YYYY-MM-DD-中文语义主题.md`.
- Names should describe the user's mental model, such as `项目日志系统搭建与规则合并` or `Tushare主数据源迁移`.
- Avoid vague names such as `update`, `misc`, `fix`, or `log1`.
- Do not maintain a separate log menu file; use `项目日志总索引.md` as the single selection surface.

## Safety

- Never write secrets or local tokens into project journal files.
- Never treat logs or archives as formal research evidence.
- If a selected log conflicts with live config, verify live config first.
- If multiple logs seem relevant, list candidates and ask the user to choose before reading deeply.
- Do not read full log bodies merely to discover what logs exist; use `项目日志总索引.md`.
