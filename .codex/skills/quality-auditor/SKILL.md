---
name: quality-auditor
description: Audits A-share sector research outputs for missing fields, semantic CSV misalignment, stale dates, duplicate source IDs, conflicts, placeholder leakage, no-source assertions, and data-source failure handling. Use after generation or when reviewing BaoStock/AKShare/Tushare/evidence pipeline results.
---

# Quality Auditor

Use this as the final gate before presenting investment research outputs.

## Entry Points

- Cleanup: `investment_system/pipelines/cleanup_outputs.py`
- Validation: `investment_system/pipelines/validate_outputs.py`
- Diagnostics: `investment_system/scripts/validate_research_client.py`
- Contract: read `references/contract.md` before adding audit checks.

## Standard Command

```powershell
# Project-aware mode (recommended):
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\pipelines\validate_outputs.py --project tech_ai_semiconductor --sector-id <sector_id>
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\pipelines\validate_outputs.py --project tech_ai_semiconductor --sector-id <sector_id> --grade research
```

## Rules

- Treat CSV semantic shifts as failures, even if row/column counts parse.
- Check source dates against actual latest trading date.
- Ensure no `缺失` placeholder remains unless it is intentionally listed as a gap.
- Record conflicts instead of silently choosing convenient values.
- Check Tushare fallback rows for source traceability and avoid exposing `TUSHARE_TOKEN`.
- Fail claims that imply Guosen, Wind, or iFind database access unless the user explicitly supplied that source data.
- Do not delete files during audit.
- For research-grade output, fail reports that contain debug placeholders outside the data-gap section.
- For research-grade output, fail source rows that have neither a local cache path nor an http(s) URL.
