---
name: quality-auditor
description: Audits A-share sector research outputs for missing fields, semantic CSV misalignment, stale dates, duplicate source IDs, conflicts, placeholder leakage, no-source assertions, and data-source failure handling. Use after generation or when reviewing BaoStock/AKShare/Tushare/evidence pipeline results.
---

# Quality Auditor

Use this as the final gate before presenting investment research outputs.

## Entry Points

- Validation: `investment_system/pipelines/validate_outputs.py`
- Standard sector stage gate: `investment_system/pipelines/sector_research/run_sector_stage.py`
- Curated evidence validation: `investment_system/pipelines/sector_research/validate_curated_evidence.py`
- Project stage policy: `investment_system/research/projects/tech_ai_semiconductor/workflow_stages.yaml`
- Diagnostics: `investment_system/scripts/validate_research_client.py`
- Contract: read `references/contract.md` before adding audit checks.
- Research-grade review standard: read `references/research_grade_standard.md` when auditing investment-reading-ready reports.

## Standard Command

```powershell
# Project-aware mode (recommended):
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" -m investment_system.pipelines.sector_research.run_sector_stage --project tech_ai_semiconductor --sector-id <sector_id> --stage evidence_gate
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" -m investment_system.pipelines.sector_research.run_sector_stage --project tech_ai_semiconductor --sector-id <sector_id> --stage candidate_gate
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" -m investment_system.pipelines.sector_research.run_sector_stage --project tech_ai_semiconductor --sector-id <sector_id> --stage publish_gate --publish-scope sector_card_only
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" -m investment_system.pipelines.sector_research.run_sector_stage --project tech_ai_semiconductor --sector-id <sector_id> --stage post_publish_check
```

Use direct `validate_outputs.py` only when debugging the underlying contract or when a stage runner step reports that output validation failed.

## Gate Responsibilities

- Evidence Gate checks evidence binding, evidence schema, and target-sector coverage. It may treat unrelated P0/P1 MISSING sectors as warning-only when the target sector is OK and `workflow_stages.yaml` allows that rule.
- Curated Evidence Validation checks that source manifests have been converted into manually reviewed active evidence, with real excerpts, claims, metrics, limitations, and missing_fields.
- Candidate Gate checks candidate structure, source/evidence closure, missing evidence retention, conflict/counter-evidence sections, no draft placeholders, no investment advice, and no formal rating.
- Publish Gate is a dry-run publication boundary check. It verifies `sector_card_only`, project-aware target paths, no-overwrite risk, source hashes, excluded outputs, and no formal directory writes.
- Post-publish Check verifies hash equality, formal card count, no forbidden formal artifacts, validate_outputs, readiness, and publish log traceability.

## Rules

- Treat CSV semantic shifts as failures, even if row/column counts parse.
- Check source dates against actual latest trading date.
- Ensure no `缺失` placeholder remains unless it is intentionally listed as a gap.
- Record conflicts instead of silently choosing convenient values.
- Check Tushare fallback rows for source traceability and avoid exposing `TUSHARE_TOKEN`.
- Fail claims that imply Guosen, Wind, or iFind database access unless the user explicitly supplied that source data.
- Do not delete files during audit.
- Treat stage policy from `workflow_stages.yaml` as the source of truth for warning-only exit handling and formal-output write boundaries.
- Fail candidate or research-grade outputs containing `DRAFT_PLACEHOLDER`, `TODO_MANUAL_EXTRACTION`, `draft_source_skeleton`, or `EV-DRAFT-` references.
- Fail candidate or formal outputs that contain buy/sell/build/add/reduce/clear-position wording, target price, position sizing, A/B/C/D/E ratings, or formal scoring unless a separate explicit scoring/investment process is in scope.
- Do not use legacy broad validation as the default workflow entry point; use `run_sector_stage.py` stages first.
- For research-grade output, fail reports that contain debug placeholders outside the data-gap section.
- For research-grade output, fail source rows that have neither a local cache path nor an http(s) URL.
