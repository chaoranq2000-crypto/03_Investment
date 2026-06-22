---
name: research-writer
description: Writes standardized A-share sector research deliverables, including theme cards, company financial valuation tables, cross-theme comparison tables, source indexes, missing-data logs, conflict logs, and research logs. Use after market, financial, evidence, and forecast layers are ready.
---

# Research Writer

Use this as the output-generation layer. It writes deliverables from collected data and curated evidence.

## Entry Points

- Standard pipeline: `investment_system/pipelines/run_research.py`
- Evidence merge: `investment_system/pipelines/evidence_overrides.py`
- Cleanup: `investment_system/pipelines/cleanup_outputs.py`
- Contract: read `references/contract.md` before changing output schemas.

## Standard Command

```powershell
# Project-aware mode (recommended):
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\pipelines\run_research.py --project tech_ai_semiconductor --sector-id <sector_id> --skip-guosen
# After generation:
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\pipelines\cleanup_outputs.py
```

## Rules

- Generate from raw data and evidence inputs; do not hand-edit final outputs as source data.
- Append during generation, then deduplicate by key in cleanup.
- Preserve output schemas expected by validation.
- Keep remaining gaps explicit in `缺失数据清单.md`.
- For research-grade reports, do not use `card_markdown` from evidence unless the evidence is explicitly marked as reviewed/research-grade.
- Every key conclusion in a research-grade report must point to a local cache path or webpage URL through `数据来源索引.csv`.
- Keep unresolved interface failures in the data-gap section; do not scatter `待核实` placeholders through the main prose.
