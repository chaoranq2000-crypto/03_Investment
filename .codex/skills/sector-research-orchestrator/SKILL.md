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

## Workflow

Use the skill CLI entry points first. The current standard flow is:

`scope_check -> evidence_collect -> evidence_draft -> manual curate -> evidence_register -> evidence_gate -> generate_candidate -> candidate_gate -> publish_gate -> manual confirmation -> publish_sector_card_only -> post_publish_check`.

The skill CLIs delegate to project-local skill modules and read project-specific stage policy from `investment_system/research/projects/<project_id>/workflow_stages.yaml`. Removed pipeline wrappers and broad-runner compatibility modules must not be reintroduced.

1. Inspect current outputs, docs, registry rows, and pipeline scripts.
2. Use `sector-research-orchestrator scope-check` before a new phase.
3. Invoke `market-data-router` and `financial-data-router` for structured market/financial inputs.
4. Invoke `evidence-miner` for annual-report, announcement, IR, Q&A, policy, and broker evidence.
5. Use `evidence-miner collect` to build source manifests from cached official files.
6. Use `evidence-miner draft` to build draft evidence YAML skeletons under the project audit directory.
7. Curate source excerpts and claims before promoting a draft into `investment_system/research/evidence/`.
8. Register evidence with `evidence-miner register` or `register-apply` instead of editing `evidence_file_ids[]` by hand.
9. Use `quality-auditor evidence-gate` after evidence changes.
10. Use `research-writer generate-candidate` and `quality-auditor candidate-gate` only when the user asks for candidate generation.
11. Use `sector-research-orchestrator publish-gate` for dry-run path/no-overwrite checks. It must not write the formal directory.
12. Use explicit manual confirmation, `sector-research-orchestrator publish-sector-card-only`, then `quality-auditor post-publish-check` for formal sector-card-only publication.
13. Loop back to the failing lower skill if validation fails.

## Commands

Use the project Conda runtime:

```powershell
# Scope check:
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\sector-research-orchestrator\scripts\cli.py scope-check --project tech_ai_semiconductor

# Official source manifest collection (preview by default; add --write-manifest to write raw manifest):
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\evidence-miner\scripts\cli.py collect --project tech_ai_semiconductor --sector-id <canonical_sector_id> --local-dir investment_system/data/raw/cninfo/<source_set>/<date> --extensions .pdf

# Draft evidence skeleton generation (preview by default; add --write-draft to write under project audits):
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\evidence-miner\scripts\cli.py draft --project tech_ai_semiconductor --sector-id <canonical_sector_id> --source-manifest investment_system/data/raw/official_evidence/<project>/<sector>/<date>/source_manifest_<sector>_<source_set>_<date>.json

# Safe evidence registration (dry-run by default; use register-apply only when writing is intended):
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\evidence-miner\scripts\cli.py register --project tech_ai_semiconductor --sector-id <canonical_sector_id> --path investment_system/research/evidence/<file>.yaml

# Candidate-only generation and gate:
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\research-writer\scripts\cli.py generate-candidate --write-candidate --project tech_ai_semiconductor --sector-id <canonical_sector_id>
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\quality-auditor\scripts\cli.py candidate-gate --project tech_ai_semiconductor --sector-id <canonical_sector_id>

# Publish dry-run and post-publish checks. Formal publish requires separate user confirmation:
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\sector-research-orchestrator\scripts\cli.py publish-gate --project tech_ai_semiconductor --sector-id <canonical_sector_id> --publish-scope sector_card_only
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\quality-auditor\scripts\cli.py post-publish-check --project tech_ai_semiconductor --sector-id <canonical_sector_id>

# Stage runner, only when a single stage shortcut is needed:
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\sector-research-orchestrator\scripts\cli.py run-stage --project tech_ai_semiconductor --sector-id <canonical_sector_id> --stage evidence_gate
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
