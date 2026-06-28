# Architecture

This is the current architecture reference for Codex operators.

## Active Project Boundary

- `investment_system/` is the reusable research engine.
- `investment_system/research/projects/<project_id>/` contains project-specific configuration.
- `investment_system/research/evidence/` is the durable evidence layer.
- `科技主线调研输出/` is generated formal output, not a source of truth.
- `.codex/skills/` contains Codex operational guidance; Python scripts do not automatically load these files.
- `.codex/skills/*/scripts/cli.py` is the preferred human-facing workflow interface in Phase 5; `investment_system.pipelines.*` modules remain compatibility wrappers for one validation cycle.

The active project instance is `tech_ai_semiconductor`. Use canonical `sector_id` as the internal sector key. Treat `main_theme`, `sub_theme`, display names, aliases, and old theme registry rows as compatibility surfaces only.

## Layer Model

1. Data layer
   - Raw API returns, PDFs, OCR/MinerU text, Tushare cache splits, and diagnostics.
   - Store under `investment_system/data/raw/` with source/dataset/date partitions.

2. Evidence layer
   - Source manifests index raw material.
   - Draft evidence skeletons stay under project audits and may contain placeholders.
   - Active evidence YAML under `investment_system/research/evidence/` is the durable research input.

3. Candidate layer
   - Candidate cards are review artifacts under project audits.
   - Candidate generation must not write the formal output root.
   - Candidate Gate checks source/evidence closure, missing evidence, conflict/counter-evidence, no placeholders, no investment advice, and no formal rating.

4. Formal sector-card layer
   - The simplified formal path supports sector-card-only publication after explicit user confirmation.
   - Publish Gate is dry-run only.
   - `publish_sector_card_only` writes exactly one sector card plus audit log when allowed.
   - Post-publish Check verifies hash equality, formal card count, and forbidden artifact absence.

5. Deferred layers
   - Formal scoring, A/B/C/D/E ratings, target prices, position sizing, and buy/sell/add/reduce/clear-position actions are out of scope unless the user explicitly starts a separate scoring or investment-decision workflow.
   - Portfolio, risk, and decision-card directories are reserved for future workflows.

## Evidence Discipline

Unsupported claims must end in one of these states:

1. backed by a local cache, active evidence YAML, or URL-bearing source;
2. recorded as missing evidence / risk / conflict / counter-evidence;
3. excluded from candidate or formal prose.

Do not promote seed documents, final Markdown, retired outputs, or context-only notes to research-grade evidence.

## Formal Output Safety

- Resolve formal paths through project-aware loaders or output contracts.
- Do not hard-code `科技主线`, sector names, or output subdirectories in generic pipeline code.
- Do not write total tables, formal source indexes, formal logs, comparison tables, score tables, ratings, or investment advice during the simplified sector-card-only workflow.
- Do not overwrite existing formal sector cards unless the user explicitly asks for an overwrite flow and the relevant gates support it.
