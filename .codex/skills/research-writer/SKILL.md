---
name: research-writer
description: Writes standardized A-share sector research deliverables, including theme cards, company financial valuation tables, cross-theme comparison tables, source indexes, missing-data logs, conflict logs, and research logs. Use after market, financial, evidence, and forecast layers are ready.
---

# Research Writer

Use this as the output-generation layer. It writes deliverables from collected data and curated evidence.

## Entry Points

- Candidate-only sector card generation: `.codex/skills/research-writer/scripts/cli.py generate-candidate --write-candidate`
- Output validation: `.codex/skills/quality-auditor/scripts/cli.py validate-outputs`
- Contract: read `references/contract.md` before changing output schemas.

## Standard Command

```powershell
# Candidate-only mode for the current simplified workflow:
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\research-writer\scripts\cli.py generate-candidate --write-candidate --project tech_ai_semiconductor --sector-id <sector_id>
```

## Rules

- Generate from raw data and evidence inputs; do not hand-edit final outputs as source data.
- Prefer project-aware writers that emit validated records directly; do not rely on a standalone cleanup script to repair outputs after generation.
- Preserve output schemas expected by validation.
- Keep remaining gaps explicit in `缺失数据清单.md`.
- For research-grade reports, do not use `card_markdown` from evidence unless the evidence is explicitly marked as reviewed/research-grade.
- Every key conclusion in a research-grade report must point to a local cache path or webpage URL through `数据来源索引.csv`.
- Keep unresolved interface failures in the data-gap section; do not scatter `待核实` placeholders through the main prose.
- Candidate generation writes only under the project audit directory; it must not publish gated formal files, release manifests, total tables, formal source indexes, scoring tables, ratings, target prices, position sizing, or investment advice.
