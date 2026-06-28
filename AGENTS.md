# [AGENTS.md](http://AGENTS.md)

## Project identity

This repository is an A-share investment research workspace.

The long-term goal is to evolve the previous one-off A-share technology-sector research workflow into a reusable sector research engine plus project-specific research instances.

Current primary project instance:

- `tech_ai_semiconductor`
- project path: `investment_system/research/projects/tech_ai_semiconductor/`
- output root: `C:\Projects\03_Investment\科技主线调研输出`

The system is still an engineering and validation workflow unless the user explicitly asks for formal research production.

---

## Directory roles

- `investment_system/` is the reusable research engine.
- `investment_system/config/` contains data-source and environment configuration examples.
- `investment_system/data/` contains raw, processed, and cached data.
- `investment_system/pipelines/` contains executable pipeline, validation, audit, cleanup, and collection code.
- `investment_system/pipelines/sector_research/` contains project-aware sector research utilities and audit tools.
- `investment_system/research/evidence/` contains structured evidence files.
- `investment_system/research/projects/<project_id>/` contains project-specific configuration.
- `investment_system/research/templates/` contains reusable output templates.
- `investment_system/research/schemas/` contains schema contracts.
- `investment_system/decisions/` contains operation decision cards and state-layering materials.
- `investment_system/portfolio/` is reserved for portfolio management.
- `investment_system/risk/` is reserved for risk review.
- `科技主线调研输出/` is an output artifact directory, not a source of truth.
- `.codex/skills/` contains reusable Codex workflow skills.
- `.conda/investment-system/` is the local Python runtime.
- `tools/` contains temporary or legacy helper scripts.
- `.agents/` is reserved for future agent definitions and should not be used unless explicitly requested.

---

## Architecture principles

- Use `project_id` as the project entry point.
- Use canonical `sector_id` as the only internal sector key in project-aware mode.
- Treat `main_theme`, `sub_theme`, legacy theme names, and aliases as legacy/display compatibility only.
- Do not use `main_theme` or `sub_theme` as project-aware primary keys.
- Use `stock_universe.yaml` as the project-aware stock source.
- Treat `KNOWN_COMPANIES` as legacy-only compatibility unless explicitly instructed otherwise.
- Bind evidence through canonical `sector_id` in project-aware mode.
- Prefer extending configuration, schemas, loaders, adapters, and audits before rewriting generic pipelines.
- Keep the reusable engine independent from the `tech_ai_semiconductor` project instance.
- Keep project-specific settings under `investment_system/research/projects/<project_id>/`.

---

## Hard constraints

- Do not move, delete, or overwrite existing research outputs unless explicitly instructed.
- Do not treat `科技主线调研输出/` as a source of truth.
- Do not treat retired legacy outputs as active evidence.
- Do not treat seed documents as formal evidence.
- Do not use seed documents for evidence, score, rating, source_id-backed claims, or investment conclusions.
- Do not hard-code `科技主线`, `高速光模块`, `CPO`, `PCB`, or fixed output paths in generic pipeline code.
- Do not use `THEME_REGISTRY_CSV` as the project-aware sector registry.
- Do not use `KNOWN_COMPANIES` as the project-aware stock source.
- Do not generate formal investment conclusions unless evidence/source_id and output schema requirements are satisfied.
- Do not generate formal build-position ratings in preview, mock, audit, or dry-run mode.
- Do not write formal output files when the task asks for preview, dry-run, audit, or mock output only.
- Do not silently promote old evidence files to research-grade status.
- Do not remove legacy compatibility unless the user explicitly asks for a breaking cleanup.
- Do not rename evidence YAML files unless explicitly instructed.
- Do not invent stock codes, source IDs, evidence IDs, or financial data.
- Do not mix TTM, annual actuals, forecasts, and consensus estimates without explicit period labels.

---

## Runtime

Use the project Python runtime:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe

```

Prefer module execution from the repository root:

```powershell
cd C:\Projects\03_Investment

```

When writing commands, use the project runtime explicitly unless the surrounding script already does so.

---

## Common validation commands

Load the project configuration:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.load_project --project tech_ai_semiconductor --json

```

Preview output path resolution:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.load_project --project tech_ai_semiconductor --dry-run-paths

```

Run pipeline readiness audit:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.audit_pipeline_readiness --project tech_ai_semiconductor

```

Run stock universe audit:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.audit_stock_universe --project tech_ai_semiconductor

```

Run evidence binding audit when evidence bindings are changed:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.audit_evidence_bindings --project tech_ai_semiconductor

```

Run evidence schema audit when evidence schema or evidence YAML files are changed:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.audit_evidence_schema --project tech_ai_semiconductor

```

Run output schema audit when output contracts are changed:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.audit_output_schema --project tech_ai_semiconductor

```

Run mock output audit when mock output generation changes:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.audit_mock_outputs --project tech_ai_semiconductor

```

Run output validation:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.validate_outputs --project tech_ai_semiconductor

```

If a command is unavailable, inspect the corresponding module and report the correct command instead of guessing.

---

## Project-aware workflow rules

- New generic pipeline code should accept `--project` or receive a loaded project config.
- New sector-specific operations should accept canonical `sector_id`.
- Use loader helper functions instead of manually re-reading project YAML files when possible.
- Resolve sector output paths through loader or output contract helpers.
- Resolve stock lists through `get_stocks_for_sector()` or equivalent project-aware helper.
- Resolve evidence files through `resolve_evidence_files_for_sector()` or equivalent project-aware helper.
- Keep loader-only inspection read-only unless the task explicitly asks for generation.
- Keep mock, preview, dry-run, and formal output modes clearly separated.
- Keep formal outputs out of audit/mock directories unless explicitly requested.
- Keep audit artifacts under the project audit directory when possible.
- Keep legacy mode working unless the user explicitly asks to remove it.
- After changing project-aware code, run the most relevant audit command.

---

## Evidence and research rules

- Every formal research claim must be traceable to `source_id` or be recorded in a missing-data log.
- Every formal evidence item should have deterministic `evidence_id` when possible.
- Evidence must bind to canonical `sector_id` in project-aware mode.
- Evidence files may retain old fields for backward compatibility.
- Old evidence YAML files should not be promoted to research-grade status without audit.
- Missing data is acceptable if it is explicitly recorded.
- Conflicting data is acceptable only if it is explicitly recorded in a conflict log.
- Financial fields must include the relevant fiscal period or reporting period.
- Forecast fields must distinguish actuals, TTM, 2026E, 2027E, consensus estimates, and internal estimates.
- Market data should include data date and source metadata.
- Research-writer logic should write from structured evidence, market data, financial data, scoring results, and missing/conflict logs.
- Research-writer logic should not invent new investment views that are unsupported by evidence.
- Quality-auditor logic should check source IDs, evidence IDs, schema conformity, legacy hardcoding, missing data, conflict data, and deprecated fields.

---

## Output rules

- Use output contracts from `investment_system/research/schemas/` and project configuration.
- Use templates from `investment_system/research/templates/`.
- Do not hard-code output columns in multiple places when a schema or contract already defines them.
- Project-aware company tables should prefer canonical fields such as `project_id`, `sector_id`, `sector_name`, `research_group_id`, `stock_code`, `stock_name`, `market`, `role`, `exposure_type`, `coverage_status`, `data_status`, `financial_period`, `source_ids`, `evidence_ids`, `missing_fields`, and `conflict_flags`.
- Legacy fields such as `main_theme` and `sub_theme` may be preserved for display or compatibility, but they must not drive project-aware joins or primary-key logic.
- Mock outputs must stay under audit/mock directories.
- Preview outputs must be clearly marked as preview and must not be confused with formal research outputs.
- Formal outputs should not be generated unless the user explicitly asks for formal output generation and validation gates are satisfied.

---

## Codex skills guidance

Existing skills should be preserved and made project-aware rather than replaced wholesale.

Current expected skill roles:

- `sector-research-orchestrator`: coordinates project-aware sector research workflow.
- `market-data-router`: routes market data collection and trading heat inputs.
- `financial-data-router`: routes financial data and valuation inputs with period/source discipline.
- `evidence-miner`: extracts and structures evidence; does not write final reports directly.
- `forecast-normalizer`: normalizes actual, TTM, forecast, and consensus data.
- `research-writer`: generates outputs only from structured inputs and schemas.
- `quality-auditor`: checks schema, source, evidence, legacy, and output quality gates.

Do not create new skills for one-off refactors.

Create or modify a skill only when the workflow is repeated, stable, has defined inputs/outputs, and has clear validation criteria.

Prefer workflow-stage skills over theme-specific skills. Do not create skills like `cpo-skill` or `pcb-skill` for a reusable sector research engine.

---

## Change discipline

Before editing:

- Inspect the relevant files.
- Identify whether the requested task is audit-only, preview, mock, or formal generation.
- Identify whether the task is project-aware or legacy-only.
- Prefer small, reversible patches.
- Do not rewrite large modules when an adapter or helper function is sufficient.

When editing:

- Preserve backward compatibility unless explicitly instructed otherwise.
- Keep path handling safe.
- Avoid global side effects in loader and audit code.
- Avoid generating directories or outputs during pure validation unless explicitly required.
- Use deterministic IDs for generated schema/evidence/source records when possible.
- Keep error and warning messages actionable.

After editing:

- Run the most relevant validation command.
- Report exactly what was changed.
- Report validation results honestly.
- List remaining risks or warnings.

---

## Validation expectations

Expected success conditions may include:

- `ERROR=0`
- `BLOCKER=0`
- `HIGH=0` when the task targets production readiness
- no invalid canonical `sector_id` references
- no invalid stock-sector references
- no duplicate stock code/name problems
- no active use of retired legacy outputs
- no seed document used as formal evidence
- no formal investment conclusion in preview, mock, audit, or dry-run mode
- no formal output write during mock or audit mode
- no deprecated project-aware fields used as primary keys
- no missing source metadata in newly created formal evidence

Warnings may remain if they are explicitly documented, non-blocking, and outside the task scope.

If validation cannot run, explain why and provide the exact command that should be run manually.

---

## Completion report

At the end of each task, report:

1. Files modified
2. Files added
3. Files inspected but not changed
4. Commands run
5. Validation result
6. Remaining warnings or risks
7. Recommended next step

Do not claim full success if validation was not run.

Do not hide partial failure.

Do not present mock, preview, or dry-run output as formal research output.

---

## Current caution

This repository may contain legacy scripts, retired outputs, old evidence mappings, and temporary tools from the original technology-sector workflow.

Treat them as migration context unless the user explicitly asks to reuse or refactor them.

The default direction is:

- reusable engine first
- project-aware configuration second
- evidence/source traceability third
- output schema compliance fourth
- formal research production last
