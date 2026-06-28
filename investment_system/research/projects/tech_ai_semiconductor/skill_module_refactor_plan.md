# Skill Module Refactor Plan

Created: 2026-06-28
Scope: `tech_ai_semiconductor` project-aware research workflow and current project-local Codex skills
Status: design draft, safe to update during implementation

This file is the working design table for migrating from a pipeline-centered runtime to a skill-module-centered runtime. It is not a formal research output, not investment advice, and not a generated sector artifact.

## 1. Goal

Make each project-local skill independently runnable, debuggable, and maintainable while preserving one shared project core.

Target outcome:

- each skill owns a stable CLI under `.codex/skills/<skill>/scripts/cli.py`;
- each skill can be tested from the repository root with the project Conda Python;
- shared project semantics stay in `investment_system/core/`;
- existing `investment_system.pipelines.*` entry points remain as compatibility wrappers until migration gates pass;
- project workflow stages reference skill CLIs after each stage is migrated and validated.

Non-goal:

- do not duplicate project loading, output path resolution, schema loading, evidence-file resolution, or source/evidence ID rules inside every skill;
- do not move, delete, or overwrite formal research outputs;
- do not promote preview, mock, draft, or audit outputs into formal outputs;
- do not remove legacy compatibility until a separate breaking-cleanup step is explicitly approved.

## 2. Target Architecture

```text
investment_system/
  core/
    __init__.py
    project_loader.py
    path_resolver.py
    schema_registry.py
    evidence_registry.py
    output_contracts.py
    audit_types.py
    data_sources/
      tushare_client.py
      research_client_adapter.py

.codex/skills/
  sector-research-orchestrator/
    SKILL.md
    scripts/cli.py
    src/sector_research_orchestrator/
    references/
    tests/

  market-data-router/
    scripts/cli.py
    src/market_data_router/
    references/
    tests/

  financial-data-router/
    scripts/cli.py
    src/financial_data_router/
    references/
    tests/

  evidence-miner/
    scripts/cli.py
    src/evidence_miner/
    references/
    tests/

  forecast-normalizer/
    scripts/cli.py
    src/forecast_normalizer/
    references/
    tests/

  research-writer/
    scripts/cli.py
    src/research_writer/
    references/
    tests/

  quality-auditor/
    scripts/cli.py
    src/quality_auditor/
    references/
    tests/

investment_system/pipelines/
  ... compatibility wrappers only after migration ...
```

## 3. Stable Contracts

These contracts should be created before moving business logic.

| Contract | Owner | Purpose | Must stay shared |
|---|---|---|---|
| Project config loader | `investment_system/core` | Load `project.yaml`, stage policy, project roots, output specs | yes |
| Canonical sector resolver | `investment_system/core` | Resolve `sector_id`, names, groups, aliases | yes |
| Stock universe resolver | `investment_system/core` | Resolve stocks by project and sector | yes |
| Evidence registry | `investment_system/core` | Resolve active evidence YAML files and bindings | yes |
| Output contract registry | `investment_system/core` | Resolve output schemas and formal/audit paths | yes |
| Audit result model | `investment_system/core` | Normalize `ERROR/WARNING/INFO`, exit codes, warning-only rules | yes |
| Data-source adapters | `investment_system/core/data_sources` | Shared Tushare and `research_client` access | mostly yes |
| Skill CLI contract | each skill | `--project`, optional `--sector-id`, dry-run/write flags, JSON/text output | no, owned by skill |

## 4. Current Pipeline Mapping

The table below maps every current Python script under `investment_system/pipelines/` to its target owner.

| Current file | Lines | Target owner | Target module | Migration action | New preferred entry |
|---|---:|---|---|---|---|
| `investment_system/pipelines/sector_research/load_project.py` | 2135 | shared core | `investment_system/core/project_loader.py`, `path_resolver.py`, `evidence_registry.py`, `output_contracts.py` | split into core modules first; keep old module as wrapper | `python -m investment_system.core.project_loader --project ...` during transition |
| `investment_system/pipelines/sector_research/run_sector_stage.py` | 537 | `sector-research-orchestrator` | `.codex/skills/sector-research-orchestrator/src/sector_research_orchestrator/stage_runner.py` | migrate orchestration after skill CLIs exist; old runner delegates to skill CLIs | `python .codex/skills/sector-research-orchestrator/scripts/cli.py run-stage ...` |
| `investment_system/pipelines/sector_research/collect_official_evidence.py` | 441 | `evidence-miner` | `.codex/skills/evidence-miner/src/evidence_miner/source_manifest.py` | move source-manifest logic; preserve preview/write split | `python .codex/skills/evidence-miner/scripts/cli.py collect ...` |
| `investment_system/pipelines/sector_research/build_evidence_skeleton.py` | 344 | `evidence-miner` | `.codex/skills/evidence-miner/src/evidence_miner/draft_skeleton.py` | move draft builder; keep draft blocked from registration | `python .codex/skills/evidence-miner/scripts/cli.py draft ...` |
| `investment_system/pipelines/sector_research/register_evidence_file.py` | 307 | `evidence-miner` | `.codex/skills/evidence-miner/src/evidence_miner/register.py` | move registration logic; keep dry-run default | `python .codex/skills/evidence-miner/scripts/cli.py register ...` |
| `investment_system/pipelines/sector_research/validate_curated_evidence.py` | 167 | `evidence-miner` plus `quality-auditor` | `.codex/skills/evidence-miner/src/evidence_miner/curation_validator.py` | move validator; expose audit mirror in quality skill | `python .codex/skills/evidence-miner/scripts/cli.py validate-curated ...` |
| `investment_system/pipelines/sector_research/split_tushare_cache.py` | 215 | `evidence-miner` | `.codex/skills/evidence-miner/src/evidence_miner/tushare_cache_split.py` | move source-cache split; use shared Tushare/source metadata helpers | `python .codex/skills/evidence-miner/scripts/cli.py split-tushare-cache ...` |
| `investment_system/pipelines/sector_research/build_formal_candidate_outputs.py` | 748 | `research-writer` | `.codex/skills/research-writer/src/research_writer/candidate_outputs.py` | move candidate generation; keep formal-root writes forbidden | `python .codex/skills/research-writer/scripts/cli.py generate-candidate ...` |
| `investment_system/pipelines/sector_research/output_writers.py` | 496 | `research-writer` | `.codex/skills/research-writer/src/research_writer/output_writers.py` | move writer library after core output contracts exist | imported by writer CLI |
| `investment_system/pipelines/sector_research/build_dry_run_outputs.py` | 465 | `research-writer` | `.codex/skills/research-writer/src/research_writer/dry_run_outputs.py` | move as legacy/debug generation mode | `python .codex/skills/research-writer/scripts/cli.py build-dry-run ...` |
| `investment_system/pipelines/sector_research/build_mock_outputs.py` | 388 | `research-writer` | `.codex/skills/research-writer/src/research_writer/mock_outputs.py` | move as test fixture/mock generator | `python .codex/skills/research-writer/scripts/cli.py build-mock ...` |
| `investment_system/pipelines/sector_research/prepare_formal_publish.py` | 693 | `sector-research-orchestrator` | `.codex/skills/sector-research-orchestrator/src/sector_research_orchestrator/publish.py` | move after candidate and publish audits are stable; keep manual confirmation | `python .codex/skills/sector-research-orchestrator/scripts/cli.py publish-sector-card-only ...` |
| `investment_system/pipelines/sector_research/promote_formal_candidate_outputs.py` | 331 | `sector-research-orchestrator` | `.codex/skills/sector-research-orchestrator/src/sector_research_orchestrator/promote.py` | move as gated staging step; keep no-overwrite and forbidden-output checks | `python .codex/skills/sector-research-orchestrator/scripts/cli.py promote-candidate ...` |
| `investment_system/pipelines/sector_research/audit_pipeline_readiness.py` | 1190 | `quality-auditor` | `.codex/skills/quality-auditor/src/quality_auditor/pipeline_readiness.py` | move as top-level readiness audit; depend on core audit model | `python .codex/skills/quality-auditor/scripts/cli.py pipeline-readiness ...` |
| `investment_system/pipelines/sector_research/audit_stock_universe.py` | 622 | `quality-auditor` | `.codex/skills/quality-auditor/src/quality_auditor/stock_universe.py` | move stock universe audit; use core stock resolver | `python .codex/skills/quality-auditor/scripts/cli.py stock-universe ...` |
| `investment_system/pipelines/sector_research/audit_evidence_bindings.py` | 295 | `quality-auditor` | `.codex/skills/quality-auditor/src/quality_auditor/evidence_bindings.py` | move binding audit; use core evidence registry | `python .codex/skills/quality-auditor/scripts/cli.py evidence-bindings ...` |
| `investment_system/pipelines/sector_research/audit_evidence_schema.py` | 763 | `quality-auditor` | `.codex/skills/quality-auditor/src/quality_auditor/evidence_schema.py` | move schema audit; share curated validator with evidence skill | `python .codex/skills/quality-auditor/scripts/cli.py evidence-schema ...` |
| `investment_system/pipelines/sector_research/audit_evidence_coverage.py` | 807 | `quality-auditor` | `.codex/skills/quality-auditor/src/quality_auditor/evidence_coverage.py` | move coverage audit; preserve target-sector warning-only rules | `python .codex/skills/quality-auditor/scripts/cli.py evidence-coverage ...` |
| `investment_system/pipelines/sector_research/audit_formal_candidate_outputs.py` | 663 | `quality-auditor` | `.codex/skills/quality-auditor/src/quality_auditor/candidate_outputs.py` | move candidate gate audit | `python .codex/skills/quality-auditor/scripts/cli.py candidate-gate ...` |
| `investment_system/pipelines/sector_research/audit_formal_publish_readiness.py` | 392 | `quality-auditor` | `.codex/skills/quality-auditor/src/quality_auditor/publish_readiness.py` | move publish gate audit | `python .codex/skills/quality-auditor/scripts/cli.py publish-gate ...` |
| `investment_system/pipelines/sector_research/audit_formal_publish_result.py` | 369 | `quality-auditor` | `.codex/skills/quality-auditor/src/quality_auditor/publish_result.py` | move post-publish audit | `python .codex/skills/quality-auditor/scripts/cli.py post-publish-check ...` |
| `investment_system/pipelines/sector_research/audit_gated_formal_outputs.py` | 349 | `quality-auditor` | `.codex/skills/quality-auditor/src/quality_auditor/gated_outputs.py` | move gated staging audit | `python .codex/skills/quality-auditor/scripts/cli.py gated-outputs ...` |
| `investment_system/pipelines/sector_research/audit_output_schema.py` | 347 | `quality-auditor` | `.codex/skills/quality-auditor/src/quality_auditor/output_schema.py` | move output contract audit | `python .codex/skills/quality-auditor/scripts/cli.py output-schema ...` |
| `investment_system/pipelines/sector_research/audit_mock_outputs.py` | 288 | `quality-auditor` | `.codex/skills/quality-auditor/src/quality_auditor/mock_outputs.py` | move mock output audit | `python .codex/skills/quality-auditor/scripts/cli.py mock-outputs ...` |
| `investment_system/pipelines/sector_research/audit_dry_run_outputs.py` | 414 | `quality-auditor` | `.codex/skills/quality-auditor/src/quality_auditor/dry_run_outputs.py` | move dry-run output audit | `python .codex/skills/quality-auditor/scripts/cli.py dry-run-outputs ...` |
| `investment_system/pipelines/sector_research/audit_generator_previews.py` | 316 | `quality-auditor` | `.codex/skills/quality-auditor/src/quality_auditor/generator_previews.py` | move preview audit | `python .codex/skills/quality-auditor/scripts/cli.py generator-previews ...` |
| `investment_system/pipelines/validate_outputs.py` | 324 | `quality-auditor` | `.codex/skills/quality-auditor/src/quality_auditor/validate_outputs.py` | move validation entry; keep old `investment_system.pipelines.validate_outputs` wrapper | `python .codex/skills/quality-auditor/scripts/cli.py validate-outputs ...` |
| `investment_system/pipelines/tushare_client.py` | 87 | shared core plus data skills | `investment_system/core/data_sources/tushare_client.py` | move connection logic to core; expose wrappers in market/financial skills | `python .codex/skills/market-data-router/scripts/cli.py tushare-ping` |
| `investment_system/pipelines/evidence_overrides.py` | 157 | shared core plus evidence/writer/forecast skills | `investment_system/core/evidence_registry.py` or `evidence_merge.py` | convert legacy merge code to shared evidence merge API | imported by evidence/writer/forecast CLIs |
| `investment_system/pipelines/run_research.py` | 1694 | legacy broad runner split across skills | multiple skill modules plus compatibility wrapper | last migration target; keep as wrapper until all stage CLIs pass | prefer orchestrator stage flow, keep legacy command as compatibility |

## 5. Skill CLI Command Design

All CLIs should support:

- `--project <project_id>`;
- `--sector-id <canonical_sector_id>` when sector-specific;
- `--format text|json` for debuggable machine output;
- dry-run/preview defaults for write-capable actions;
- explicit write flags such as `--write-manifest`, `--write-draft`, `--apply-registration`, `--confirm-publish`;
- stable exit codes: `0=pass`, `1=error`, `2=blocker`, `3=warning-only`.

Suggested commands:

| Skill | Command group | Examples |
|---|---|---|
| `sector-research-orchestrator` | stage and publish orchestration | `run-stage`, `scope-check`, `publish-sector-card-only`, `post-publish-check` |
| `market-data-router` | market data and diagnostics | `daily-kline`, `latest-quotes`, `fund-flow`, `tushare-ping` |
| `financial-data-router` | financial data and valuation inputs | `profit`, `income`, `daily-basic`, `normalize-financials` |
| `evidence-miner` | evidence source and registration flow | `collect`, `draft`, `validate-curated`, `register`, `split-tushare-cache` |
| `forecast-normalizer` | forecast fields and forward valuation normalization | `normalize`, `audit-forecast-fields`, `merge-forecast-evidence` |
| `research-writer` | candidate and legacy output generation | `generate-candidate`, `build-dry-run`, `build-mock`, `render-sector-card` |
| `quality-auditor` | gates and validations | `pipeline-readiness`, `evidence-gate`, `candidate-gate`, `publish-gate`, `validate-outputs` |

## 6. Entry and Reference Update Matrix

These files contain old or current pipeline references and must be updated when a stage switches to skill CLI.

| File | Current role | Update timing |
|---|---|---|
| `AGENTS.md` | project-wide runtime rules and validation commands | update after core and first skill CLI wrappers exist |
| `investment_system/README.md` | high-level executable-flow summary | update after orchestrator CLI can call existing wrappers |
| `.codex/skills/*/SKILL.md` | skill entry points and command snippets | update skill-by-skill during migration |
| `.codex/skills/*/references/contract.md` | skill input/output contract | update before moving business logic for that skill |
| `.codex/skills/sector-research-orchestrator/references/workflow.md` | standard workflow commands | update after all stage-level skill CLIs exist |
| `.codex/skills/sector-research-orchestrator/references/quality_gates.md` | gate commands and acceptance | update after quality-auditor CLI exists |
| `.codex/skills/sector-research-orchestrator/references/data_sources.md` | data-source command references | update after market/financial Tushare wrappers exist |
| `.codex/skills/sector-research-orchestrator/references/architecture.md` | architecture boundary | update when shared core is introduced |
| `investment_system/research/projects/tech_ai_semiconductor/workflow_stages.yaml` | stage policy and step list | update after orchestrator stage runner delegates to skill CLIs |
| `investment_system/research/projects/tech_ai_semiconductor/project.yaml` | runtime path hints | update only if command surface or pythonpath policy changes |
| historical audit files | immutable audit evidence | do not rewrite unless explicitly asked |

## 7. Phased Implementation Plan

### Phase 0: Baseline and branch discipline

Goal: freeze the current behavior before any large rewrite.

- record `git status --short`;
- run baseline commands:
  - `C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.load_project --project tech_ai_semiconductor --json`;
  - `C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.audit_pipeline_readiness --project tech_ai_semiconductor`;
  - `C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.validate_outputs --project tech_ai_semiconductor`;
- document known warning-only behavior before migration.

Phase 0 baseline result, captured 2026-06-28:

| Check | Result | Notes |
|---|---|---|
| `git status --short` | dirty before migration | Existing deleted files: `计划.txt`, `项目重构计划.md`; this plan file is untracked until staged. |
| `load_project --project tech_ai_semiconductor --json` | exit code 1, warning-only | JSON reported `errors=[]`, `_load_status=warning`, `sector_count=29`, `stock_count=94`, `evidence_file_count=8`, 9 warnings. |
| `audit_pipeline_readiness --project tech_ai_semiconductor` | exit code 0 | `BLOCKER=0`, `HIGH=0`, `MEDIUM=0`, `LOW=26`; LOW findings are legacy/schema/evidence-readiness warnings. |
| `validate_outputs --project tech_ai_semiconductor` | exit code 0 | Validation passed; output contract loaded 7 output types; `formal_outputs_found=0`; total/log directories not yet created. |

Baseline interpretation:

- The project is safe to start Phase 1 from a structural-validation perspective.
- `load_project` warning-only nonzero behavior is part of the baseline and must not be treated as a migration blocker unless `errors` becomes non-empty.
- No formal research output was generated by the baseline commands.
- Existing deleted files were present before this baseline and are outside this refactor step.

### Phase 1: Create shared core without moving business logic

Goal: make project semantics importable from `investment_system/core`.

- create `investment_system/core/`;
- extract project config, path, evidence, output contract, schema, and audit result helpers from `load_project.py`;
- update old pipeline modules to import from core;
- keep old commands working.

Phase 1A progress result, captured 2026-06-28:

| Check | Result | Notes |
|---|---|---|
| Core facade created | done | Added `investment_system/core/` with project loader, path resolver, evidence registry, output contracts, schema registry, audit types, and Tushare data-source facade. |
| Business logic moved | not yet | Phase 1A intentionally delegates to existing `investment_system.pipelines.*` modules; no legacy pipeline command was removed or rewritten. |
| New core import smoke test | exit code 0 | `from investment_system.core import load_project` loaded `tech_ai_semiconductor`; output contract count was 7. |
| New project-loader facade CLI | warning-only parity | `python -m investment_system.core.project_loader --project tech_ai_semiconductor --json` returned the same warning-only shape as the legacy loader: `errors=[]`, `_load_status=warning`. |
| New dry-run path facade CLI | exit code 0 | `python -m investment_system.core.project_loader --project tech_ai_semiconductor --dry-run-paths` resolved project paths without writing formal outputs. |
| Legacy readiness command | exit code 0 | `audit_pipeline_readiness` remained `BLOCKER=0`, `HIGH=0`, `MEDIUM=0`, `LOW=26`. |
| Legacy output validation | exit code 0 | `validate_outputs` still passed with `formal_outputs_found=0`. |

Phase 1A interpretation:

- The new shared core import surface exists and is safe for skill CLI wrappers to depend on.
- Actual extraction from `load_project.py` is still pending; the old loader remains the implementation source.
- The next Phase 1 step should move one narrow, low-risk group of pure helpers into core, then convert the old loader to import those helpers.

Phase 1B progress result, captured 2026-06-28:

| Check | Result | Notes |
|---|---|---|
| Core constants added | done | Added `investment_system/core/constants.py` for `WORKSPACE_ROOT`, `PROJECTS_ROOT`, and `SCHEMAS_ROOT`, reducing core schema/path helpers' dependency on the legacy loader. |
| Path helpers extracted | done | `safe_filename()`, `resolve_sector_card_path()`, and `resolve_output_paths()` now have standalone implementations in `investment_system/core/path_resolver.py`. |
| Output contract helpers extracted | done | `get_output_spec()`, `get_output_schema()`, `list_output_types()`, `get_output_contract()`, `resolve_output_path()`, and `validate_output_record_shape()` now have standalone implementations in `investment_system/core/output_contracts.py`. |
| Package-level core exports | done | `investment_system.core` now lazily exports the extracted path and output-contract helpers for skill CLI import stability. |
| Legacy loader reversed to core | done | `investment_system/pipelines/sector_research/load_project.py` keeps the same public helper names, but delegates the extracted pure helper group back to `investment_system.core`. |
| Core import smoke test | exit code 0 | `from investment_system.core import load_project` plus `core.output_contracts` and `core.path_resolver` loaded `tech_ai_semiconductor`; output contract count remained 7. |
| Core project-loader facade CLI | warning-only parity | `python -m investment_system.core.project_loader --project tech_ai_semiconductor --json` returned `errors=[]`, `_load_status=warning`, exit code 1, matching the existing warning-only baseline. |
| Legacy dry-run path CLI | exit code 0 | `python -m investment_system.pipelines.sector_research.load_project --project tech_ai_semiconductor --dry-run-paths` still resolved paths without formal writes. |
| Legacy readiness command | exit code 0 | `audit_pipeline_readiness` remained `BLOCKER=0`, `HIGH=0`, `MEDIUM=0`, `LOW=26`. |
| Legacy output validation | exit code 0 | `validate_outputs` still passed with `formal_outputs_found=0`. |

Phase 1B interpretation:

- The first true extraction is complete for path and output-contract pure helpers.
- Old pipeline callers can keep importing from `load_project.py`, while new skill modules can import the same behavior directly from `investment_system.core`.
- `load_project.py` still owns the project dataclass, validation flow, evidence resolver, stock resolver, sector lookup helpers, and CLI presentation code.
- The next Phase 1 step should extract another small pure group, preferably schema-loading helpers and/or evidence-file resolver helpers, before touching larger validation flow.

Phase 1C progress result, captured 2026-06-28:

| Check | Result | Notes |
|---|---|---|
| Evidence registry extracted | done | `investment_system/core/evidence_registry.py` now owns `build_legacy_sector_map()`, `resolve_sector_id()`, `get_sector()`, `list_scoring_sectors()`, `get_stocks_for_sector()`, and `resolve_evidence_files_for_sector()`. |
| Legacy loader reversed to evidence registry | done | `investment_system/pipelines/sector_research/load_project.py` keeps the same public sector/stock/evidence helper names, but delegates to `investment_system.core.evidence_registry`. |
| Package-level core exports | done | `investment_system.core` now lazily exports sector, stock, and evidence registry helpers for skill CLI import stability. |
| Core smoke test | exit code 0 | `from investment_system.core import load_project, get_sector, get_stocks_for_sector, resolve_evidence_files_for_sector, resolve_sector_id` loaded `tech_ai_semiconductor`; `high_speed_copper_connector` resolved to 5 stocks and 3 evidence files. |
| Legacy helper smoke test | exit code 0 | The same `get_sector()`, `get_stocks_for_sector()`, and `resolve_evidence_files_for_sector()` calls still work through the legacy `load_project.py` import path. |
| Evidence binding audit | exit code 0 | `audit_evidence_bindings` reported `ERROR=0`, `WARNING=15`, `INFO=12`; warnings are existing missing-evidence and legacy-compatibility items. |
| Stock universe audit | exit code 0 | `audit_stock_universe` reported `ERROR=0`, `WARNING=3`, with P0/P1 threshold coverage intact. |

Phase 1C interpretation:

- Sector ID resolution, stock lookup, and evidence-file binding now have a stable core implementation for future skill CLIs.
- `load_project.py` still owns the project dataclass, YAML loading, validation flow, and CLI presentation.
- The remaining large extraction risk is the validation flow; the next safe step should move only generic schema-loading helpers or validation warning primitives before any loader rewrite.

Phase 1D progress result, captured 2026-06-28:

| Check | Result | Notes |
|---|---|---|
| Validation warning primitive extracted | done | `ValidationWarning` now lives in `investment_system/core/audit_types.py`; the legacy loader imports and re-exports the same class through its existing public name. |
| YAML helper extraction | done | `load_yaml()` and `get_nested()` now live in `investment_system/core/schema_registry.py`; legacy `load_project.py` keeps wrapper functions for compatibility. |
| Schema registry helper reuse | done | `load_schema()` now delegates file reading through the shared `load_yaml()` helper. |
| Package-level core exports | done | `investment_system.core` now lazily exports `ValidationWarning`, `load_yaml()`, and `get_nested()` for skill CLI import stability. |
| Helper smoke test | exit code 0 | Core and legacy imports for `ValidationWarning`, `load_yaml()`, and `get_nested()` produced the same shapes; `load_schema("output.schema.yaml")` loaded 7 output types. |
| Core project-loader facade CLI | warning-only parity | `python -m investment_system.core.project_loader --project tech_ai_semiconductor --json` returned `errors=[]`, `_load_status=warning`, exit code 1, preserving the baseline. |
| Output schema audit | exit code 0 | `audit_output_schema` reported `ERROR=0`, `WARNING=0`, `INFO=1`, with 7 output types loaded. |
| Legacy readiness command | exit code 0 | `audit_pipeline_readiness` remained `BLOCKER=0`, `HIGH=0`, `MEDIUM=0`, `LOW=26`. |
| Legacy output validation | exit code 0 | `validate_outputs` still passed with `formal_outputs_found=0`. |

Phase 1D interpretation:

- The shared audit/schema primitives are now safe for future skill CLI wrappers.
- `load_project.py` still owns the main validation flow, `ProjectConfig`, and CLI output behavior.
- The next step should either stop Phase 1 extraction here and start Phase 2 CLI wrappers, or do one final Phase 1E pass to move only project constants/config-file names into core without rewriting validation control flow.

Phase 1E progress result, captured 2026-06-28:

| Check | Result | Notes |
|---|---|---|
| Project contract constants extracted | done | Added `investment_system/core/project_contracts.py` for required project files, required output spec fields, seed safety constants, stock-code pattern, AI app parent-chain exclusions, and unregistered-MD scan exclusions. |
| Legacy loader imports contracts from core | done | `investment_system/pipelines/sector_research/load_project.py` no longer owns those static contract definitions; it imports the same names from `investment_system.core.project_contracts`. |
| Package-level core exports | done | `investment_system.core` now lazily exports the project contract constants needed by future skill CLI wrappers. |
| Contract smoke test | exit code 0 | Core and legacy imports for `REQUIRED_PROJECT_FILES` matched; `STOCK_CODE_PATTERN` accepted `000001.SZ` and `600000.SH`; `load_project()` still loaded `tech_ai_semiconductor`. |
| Core project-loader facade CLI | warning-only parity | `python -m investment_system.core.project_loader --project tech_ai_semiconductor --json` returned `errors=[]`, `_load_status=warning`, exit code 1, preserving the baseline. |
| Legacy dry-run path CLI | exit code 0 | `python -m investment_system.pipelines.sector_research.load_project --project tech_ai_semiconductor --dry-run-paths` still resolved paths without formal writes. |
| Legacy readiness command | exit code 0 | `audit_pipeline_readiness` remained `BLOCKER=0`, `HIGH=0`, `MEDIUM=0`, `LOW=26`. |
| Legacy output validation | exit code 0 | `validate_outputs` still passed with `formal_outputs_found=0`. |

Phase 1E interpretation:

- The low-risk Phase 1 extraction set is complete: path resolution, output contracts, evidence/sector registry, audit/schema primitives, and static project contract constants now have stable core surfaces.
- `load_project.py` still intentionally owns `ProjectConfig`, validation control flow, and CLI output behavior.
- The next step should move to Phase 2 skill CLI wrappers instead of continuing to peel the loader, unless a specific validation helper needs extraction for a wrapper.

Validation:

- `python -m py_compile` for touched modules;
- `load_project --json`;
- `load_project --dry-run-paths`;
- `audit_pipeline_readiness`;
- `validate_outputs`.

### Phase 2: Add skill CLI wrappers

Goal: every skill can run independently while still delegating to old pipeline modules.

- create `scripts/cli.py` for each skill;
- create minimal `src/<skill_module>/` packages;
- add `tests/` only where the skill has deterministic pure logic or CLI wrappers to smoke-test;
- keep write-capable commands dry-run/preview by default.

Validation:

- smoke-test each CLI with `--help`;
- run non-writing commands for `tech_ai_semiconductor`;
- run write-capable commands only in preview/dry-run mode unless explicitly authorized.

Phase 2 progress result, captured 2026-06-28:

| Check | Result | Notes |
|---|---|---|
| Shared CLI delegator | done | Added `investment_system/core/legacy_cli.py` with `LegacyCommand`, delegated `main()` invocation, command help, and explicit write-confirmation guard support. |
| Skill CLI wrappers | done | Added `scripts/cli.py` and minimal `src/<skill_module>/` packages for all seven project-local skills: `sector-research-orchestrator`, `market-data-router`, `financial-data-router`, `evidence-miner`, `forecast-normalizer`, `research-writer`, and `quality-auditor`. |
| Evidence miner commands | done | Exposed `collect`, `draft`, `validate-curated`, `register`, `register-apply`, and `split-tushare-cache`; `register` delegates with `--dry-run` by default. |
| Quality auditor commands | done | Exposed project readiness, stock universe, evidence binding/schema/coverage, output schema, mock/dry-run/generator previews, validate outputs, and stage-gate wrappers. |
| Writer/orchestrator commands | done | Exposed candidate/mock/dry-run writer commands plus stage, scope, publish-gate, publish-sector-card-only, prepare-publish, promote-candidate, and post-publish wrappers. |
| Market/financial data commands | minimal wrapper done | Exposed `tushare-ping` through market and financial data router CLIs without duplicating client code. |
| Forecast normalizer CLI | explicitly deferred | Added `forecast-normalizer status`; forecast normalization logic remains deferred and must not imply Wind/iFind access. |
| CLI compile check | exit code 0 | `py_compile` passed for `legacy_cli.py` and all new skill wrapper scripts/modules. |
| CLI help smoke tests | exit code 0 | All seven `scripts/cli.py --help` commands exited 0. |
| Non-writing command tests | exit code 0 | `quality-auditor pipeline-readiness`, `quality-auditor output-schema`, `quality-auditor validate-outputs`, and `forecast-normalizer status` exited 0. |
| Write guard tests | exit code 0 | `research-writer generate-candidate ...` and `sector-research-orchestrator promote-candidate ...` without explicit write flags returned guard messages and did not delegate to write-capable legacy commands. |

Phase 2 interpretation:

- Every project-local skill now has an independently runnable CLI surface.
- Phase 2 wrappers still delegate to the old pipeline modules; business logic migration remains Phase 3/4 work.
- Write-capable skill commands either inherit legacy dry-run/preview behavior or require explicit skill-level confirmation flags before delegation.

### Phase 3: Move evidence and quality modules first

Goal: migrate the highest-value modular boundaries before generation/publish logic.

Order:

1. `evidence-miner`: source manifest, draft skeleton, curated validator, evidence registration, Tushare cache split;
2. `quality-auditor`: evidence gates, output schema, pipeline readiness, candidate gate.

Reason:

- evidence and audit modules are easier to validate without formal output writes;
- they enforce the safety gates needed before writer/publish migration.

Validation:

- `evidence_gate` equivalent through skill CLIs;
- direct old pipeline commands still delegate successfully;
- no formal output writes.

Phase 3 progress result, captured 2026-06-28:

| Check | Result | Notes |
|---|---|---|
| Evidence modules migrated | done | Moved source manifest, draft skeleton, curated validator, evidence registration, and Tushare cache split logic into `.codex/skills/evidence-miner/src/evidence_miner/`. |
| Quality modules migrated | done | Moved readiness, stock universe, evidence binding/schema/coverage, output schema, mock/dry-run/generator preview, candidate/publish/gated audits, and output validation into `.codex/skills/quality-auditor/src/quality_auditor/`. |
| Legacy entry compatibility | done | Old `investment_system.pipelines.*` evidence and quality entry modules now re-export the migrated skill modules through `investment_system.core.skill_module_loader`. |
| Cross-skill imports | done | Skill CLIs now inject all project-local skill `src` roots, so quality audits can import writer/orchestrator modules without falling back to old wrappers. |
| Evidence gate validation | exit code 0 | `quality-auditor evidence-gate --project tech_ai_semiconductor --sector-id high_speed_copper_connector` and legacy `run_sector_stage --stage evidence_gate` both completed with `blocking_count=0`; target sector coverage was OK. |
| Evidence registration dry-run | exit code 0 | `evidence-miner register ... ai_server_pcb_high_speed_board.yaml` reported `dry_run: True` and `no files written`. |
| Readiness validation | exit code 0 | Skill and legacy readiness commands both returned `BLOCKER=0`, `HIGH=0`, `MEDIUM=0`, `LOW=26`. |

Phase 3 interpretation:

- Evidence and quality ownership has moved to skill modules while legacy pipeline command names remain importable and runnable.
- The evidence registration CLI correctly distinguishes curated-ready evidence from older schema-normalized evidence and keeps registration dry-run by default.
- No formal output file was created or changed during Phase 3 validation.

### Phase 4: Move writer and publish modules

Goal: migrate candidate generation and sector-card-only publication.

Order:

1. `research-writer`: candidate generation and output writers;
2. `sector-research-orchestrator`: candidate promotion and publish execution;
3. `quality-auditor`: publish readiness and post-publish checks.

Validation:

- `generate_candidate` writes only under project audits;
- `candidate_gate` passes or reports actionable errors;
- `publish_gate` dry-run writes only manifest/readiness audit;
- formal publish remains blocked unless explicit user confirmation is given.

Phase 4 progress result, captured 2026-06-28:

| Check | Result | Notes |
|---|---|---|
| Writer modules migrated | done | Moved formal candidate generation, output writer adapters, dry-run outputs, and mock outputs into `.codex/skills/research-writer/src/research_writer/`. |
| Orchestrator modules migrated | done | Moved stage runner, publish preparation, and candidate promotion into `.codex/skills/sector-research-orchestrator/src/sector_research_orchestrator/`. |
| Legacy entry compatibility | done | Old writer/orchestrator pipeline modules now re-export migrated skill modules through `investment_system.core.skill_module_loader`. |
| Candidate write guard | exit code 0 | `research-writer generate-candidate ...` without `--write-candidate` returned the guard message and did not delegate. |
| Candidate generation | exit code 0 | `research-writer generate-candidate --write-candidate ... --sector-id high_speed_copper_connector --run-id 20260628` wrote only under project audits/formal_candidate_outputs; shape_errors=0. |
| Candidate gate | exit code 0 | `quality-auditor candidate-gate ... high_speed_copper_connector` passed after writer retained the required missing-evidence markers `named_customer_order_certification` and `ai_server_named_customer_300563`. |
| Promotion guard and gated staging | exit code 0 | `sector-research-orchestrator promote-candidate` without `--apply-promotion` returned the guard; with `--apply-promotion`, it wrote only under audits/gated_formal_outputs. |
| Publish dry-run blocked existing card safely | actionable block | `publish-gate ... high_speed_copper_connector` produced a manifest/readiness audit and correctly blocked on `target_overwrite_risk=True` because the formal sector card already exists. |
| Publish dry-run pass case | exit code 0 | `publish-gate ... ai_server_pcb_high_speed_board` returned `blocking_count=0`, `gates_passed=True`, `publish_executed=False`, and `target_overwrite_risk=False`. |
| Post-publish check | exit code 0 | `quality-auditor post-publish-check ... high_speed_copper_connector` returned `blocking_count=0`; existing formal card hash matched its publish log and no forbidden investment conclusion was found. |
| Formal root safety | passed | `科技主线调研输出/` remained 3 files with unchanged SHA256 hashes; `validate_outputs` still reported `formal_outputs_found=0`. |

Phase 4 interpretation:

- Writer and publish ownership has moved to skill modules while old pipeline entry points remain compatibility wrappers.
- Candidate and gated-formal artifacts are generated only under project audit directories.
- Formal publish remains dry-run/manual-confirmation gated; no formal output was written in Phase 4 validation.

### Phase 5: Switch project workflow references

Goal: make skill CLIs the preferred interface.

- update `workflow_stages.yaml` step names or command routing;
- update `AGENTS.md`, `investment_system/README.md`, skill `SKILL.md`, and references;
- preserve old `investment_system.pipelines.*` commands as compatibility wrappers for one full validation cycle.

Validation:

- run the full simplified chain for one non-formal target sector through skill CLI equivalents:
  - scope check;
  - evidence gate;
  - generate candidate;
  - candidate gate;
  - publish gate dry-run;
  - post-publish check only when a publish already exists.

Phase 5 completion snapshot:

| Check | Result | Notes |
|---|---|---|
| `workflow_stages.yaml` routing | done | Added `skill_cli_routing` with 10 stage mappings; each stage now records the preferred skill CLI and the old `investment_system.pipelines.*` compatibility command. |
| Project-level references | done | Updated `AGENTS.md` and `investment_system/README.md` so common validation and simplified-chain examples use skill/core facades first. |
| Skill references | done | Updated orchestrator, evidence, quality, writer, market, financial, and forecast skill entry references; updated orchestrator workflow/quality/data/architecture references and quality contract. |
| User-visible audit help text | done | Updated `pipeline_readiness.py`, `evidence_coverage.py`, and `stock_universe.py` usage examples to show `quality-auditor` CLI commands. |
| Syntax and YAML checks | exit code 0 | `py_compile` passed for touched Python help-text modules; `workflow_stages.yaml` parsed and exposed `preferred_interface=skill_cli`, `stages=10`. |
| Scope check through skill CLI | exit code 0 | `sector-research-orchestrator scope-check ... ai_server_pcb_high_speed_board` returned `blocking_count=0`; `load_project` stayed warning-only and `validate_outputs` reported `formal_outputs_found=0`. |
| Evidence gate through skill CLI | exit code 0 | `quality-auditor evidence-gate ... ai_server_pcb_high_speed_board` returned `blocking_count=0`; target coverage was `coverage OK` while unrelated P0/P1 gaps remained warning-only. |
| Candidate generation through skill CLI | exit code 0 | `research-writer generate-candidate --write-candidate ... ai_server_pcb_high_speed_board` wrote only under project audits/formal_candidate_outputs; `shape_errors=0`, `shape_warnings=8`. |
| Candidate gate through skill CLI | exit code 0 | `quality-auditor candidate-gate ... ai_server_pcb_high_speed_board` returned `ERROR=0`, `source_id_closure=True`, `evidence_id_closure=True`, and `blocking_count=0`. |
| Publish gate dry-run through skill CLI | exit code 0 | `sector-research-orchestrator publish-gate ... ai_server_pcb_high_speed_board` returned `dry_run=True`, `publish_executed=False`, `manual_confirmation_required=True`, `target_overwrite_risk=False`, and `blocking_count=0`. |
| Post-publish check for existing card | exit code 0 | `quality-auditor post-publish-check ... high_speed_copper_connector` returned `blocking_count=0`, `hash_match=True`, `formal_markdown_file_count=3`, and `no_investment_conclusion=True`. |
| Compatibility wrapper audit | exit code 0 | Old `python -m investment_system.pipelines.sector_research.run_sector_stage ... --stage candidate_gate` and old `python -m investment_system.pipelines.validate_outputs --project tech_ai_semiconductor` both passed. |
| Formal root safety | passed | `科技主线调研输出/` remained 3 files; SHA256 hashes were unchanged and `quality-auditor validate-outputs` reported `formal_outputs_found=0`. |
| Diff check | exit code 0 | `git diff --check` reported no whitespace errors; Git still printed LF-to-CRLF normalization warnings. |

Phase 5 interpretation:

- Skill CLIs are now the preferred operator-facing workflow interface.
- Old pipeline module commands are explicitly documented as compatibility wrappers, not primary entry points.
- Phase 5 validation wrote only audit/candidate/manifest artifacts under the project audit directory; no formal research output was generated or modified.

### Phase 6: Decide legacy cleanup

Goal: explicitly choose which wrappers remain.

- do not delete old pipeline wrappers automatically;
- prepare a separate deletion/deprecation list if cleanup is requested;
- delete only explicit files one by one if the user confirms.

Phase 6 completion snapshot:

| Check | Result | Notes |
|---|---|---|
| Legacy wrapper inventory | done | Identified migrated export wrappers in `investment_system/pipelines/sector_research/*.py` plus `investment_system/pipelines/validate_outputs.py`. |
| Required legacy surfaces | keep | `load_project.py`, `run_research.py`, `evidence_overrides.py`, and `tushare_client.py` still carry legacy/core-compatibility responsibilities and are not deletion candidates now. |
| Deletion decision | no deletion | No files were deleted in Phase 6. All pipeline wrappers remain until internal skill-module calls stop relying on `investment_system.pipelines.*` module names and one full validation cycle passes. |
| Separate retention plan | added | `investment_system/research/projects/tech_ai_semiconductor/audits/legacy_wrapper_retention_plan_phase6.md` records keep-required paths, keep-one-cycle wrappers, blockers, and later cleanup preconditions. |
| Pipeline directory guidance | updated | `investment_system/pipelines/README.md` now states that skill CLIs are preferred and most sector-research pipeline files are compatibility wrappers. |
| Validation | exit code 0 | `quality-auditor pipeline-readiness --project tech_ai_semiconductor` returned `BLOCKER=0`, `HIGH=0`, `MEDIUM=0`, `LOW=26`. |
| Output validation | exit code 0 | `quality-auditor validate-outputs --project tech_ai_semiconductor` passed with `formal_outputs_found=0`. |
| Formal root safety | passed | `科技主线调研输出/` remained 3 files with unchanged SHA256 hashes. |
| Diff check | exit code 0 | `git diff --check` reported no whitespace errors; Git still printed LF-to-CRLF normalization warnings. |

Phase 6 interpretation:

- Cleanup is explicitly deferred; the safe decision is retention, not deletion.
- Future cleanup should first move internal skill-module subprocess calls away from `investment_system.pipelines.*`, move the real Tushare implementation into core, and decide whether `run_research.py` remains as a legacy broad runner.
- If deletion is later requested, use an explicit path-by-path deletion list and remove one file at a time only after confirmation.

### Phase 7: Switch Internal Subprocess Calls to Skill/Core Modules

Goal: make migrated skill modules call direct skill/core modules internally instead of shelling out through old `investment_system.pipelines.*` wrapper module names.

- add a shared subprocess environment helper that exposes all project-local skill `src/` roots through `PYTHONPATH`;
- update orchestrator stage/publish subprocess calls to `quality_auditor.*`, `research_writer.*`, `evidence_miner.*`, `sector_research_orchestrator.*`, and `investment_system.core.project_loader`;
- update quality-auditor nested validation/readiness subprocess calls to direct skill/core modules;
- keep legacy pipeline wrappers in place for user compatibility and old command validation;
- do not change formal publish behavior or delete any files.

Phase 7 completion snapshot:

| Check | Result | Notes |
|---|---|---|
| Shared subprocess environment | done | Added `skill_subprocess_env()` in `investment_system/core/skill_module_loader.py` so direct `python -m <skill_module>` subprocesses can import project-local skill packages. |
| Stage runner internal calls | done | `sector_research_orchestrator.stage_runner` now calls `investment_system.core.project_loader`, `quality_auditor.*`, `evidence_miner.*`, `research_writer.candidate_outputs`, and `sector_research_orchestrator.publish` directly. |
| Publish readiness internal call | done | `sector_research_orchestrator.publish` now calls `quality_auditor.publish_readiness` directly. |
| Quality nested checks | done | `quality_auditor.candidate_outputs`, `publish_readiness`, `publish_result`, and `gated_outputs` now call `quality_auditor.validate_outputs`, `quality_auditor.pipeline_readiness`, or `investment_system.core.project_loader` directly. |
| Syntax check | exit code 0 | `py_compile` passed for all touched Python modules. |
| Scope check through direct modules | exit code 0 | `sector-research-orchestrator scope-check ... ai_server_pcb_high_speed_board` returned `blocking_count=0`; displayed commands used `investment_system.core.project_loader`, `quality_auditor.pipeline_readiness`, and `quality_auditor.validate_outputs`. |
| Evidence gate through direct modules | exit code 0 | `quality-auditor evidence-gate ... ai_server_pcb_high_speed_board` returned `blocking_count=0`; displayed commands used `quality_auditor.evidence_bindings`, `quality_auditor.evidence_schema`, and `quality_auditor.evidence_coverage`. |
| Candidate generation through direct module | exit code 0 | `sector-research-orchestrator run-stage --stage generate_candidate ... ai_server_pcb_high_speed_board` called `research_writer.candidate_outputs` directly and wrote only under audits/formal_candidate_outputs; `shape_errors=0`. |
| Candidate gate through direct module | exit code 0 | `quality-auditor candidate-gate ... ai_server_pcb_high_speed_board` called `quality_auditor.candidate_outputs` directly and returned `blocking_count=0`. |
| Publish gate dry-run through direct modules | exit code 0 | `sector-research-orchestrator publish-gate ... ai_server_pcb_high_speed_board` called `sector_research_orchestrator.publish` and `quality_auditor.publish_readiness` directly; `publish_executed=False`, `target_overwrite_risk=False`, `blocking_count=0`. |
| Post-publish check through direct modules | exit code 0 | `quality-auditor post-publish-check ... high_speed_copper_connector` called `quality_auditor.publish_result`, `quality_auditor.validate_outputs`, and `quality_auditor.pipeline_readiness` directly; `hash_match=True`, `formal_markdown_file_count=3`, `blocking_count=0`. |

Phase 7 interpretation:

- The active skill workflow no longer depends on old wrapper module names for nested subprocess execution.
- Pipeline wrappers still remain for old user commands, historical reproducibility, and loader/Tushare/broad-runner compatibility.
- Remaining `investment_system.pipelines.sector_research.load_project` imports are compatibility imports and should be addressed in the later true loader split, not by deleting wrappers now.

### Phase 8: Move Skill Imports to Core Facades and Complete Data Router CLI Wrappers

Goal: remove direct skill-module imports from old `load_project` wrappers and make market/financial router CLIs expose focused data commands through shared clients.

- make `investment_system.core.project_loader` the stable import surface for project loading, sector/stock/evidence helpers, and output contract helpers used by skills;
- update migrated skill modules to import from `investment_system.core.project_loader` instead of `investment_system.pipelines.sector_research.load_project`;
- add market-data router commands backed by `ResearchClient` with dry-run default and explicit `--fetch`;
- add financial-data router commands backed by `ResearchClient` with dry-run default and explicit `--fetch`;
- preserve old pipeline wrappers and do not delete files;
- do not write formal outputs or raw-data cache files during Phase 8 validation.

Phase 8 completion snapshot:

| Check | Result | Notes |
|---|---|---|
| Core facade expanded | done | `investment_system.core.project_loader` now exports output-contract and output-path helpers needed by migrated skills. |
| Skill imports switched | done | No `.codex/skills/**/*.py` file imports `investment_system.pipelines.sector_research.load_project` directly. |
| Market router commands migrated | done | Added `daily-kline`, `tencent-daily`, `fund-flow`, `index-daily`, and `stock-info` commands through `.codex/skills/market-data-router/scripts/cli.py`; default mode is dry-run. |
| Financial router commands migrated | done | Added `profit`, `financial-indicator`, and `normalize-financials` commands through `.codex/skills/financial-data-router/scripts/cli.py`; live pulls require `--fetch` where applicable. |
| Skill references updated | done | Updated market/financial skill entry points and orchestrator data-source reference with dry-run routing examples. |
| Core facade smoke test | exit code 0 | Imported project, sector, evidence, output-contract, and path helpers from `investment_system.core.project_loader`; loaded `tech_ai_semiconductor`, 7 output types, and 3 high-speed-copper evidence files. |
| Syntax and help checks | exit code 0 | `py_compile` passed for touched Phase 8 Python files; market and financial router `--help` commands showed the new command surfaces. |
| Dry-run router checks | exit code 0 | Market `daily-kline` and `tencent-daily`, financial `profit`, `financial-indicator`, and `normalize-financials` previews all returned dry-run payloads without live fetch or file writes. |

Phase 8 interpretation:

- Skill-owned modules no longer import the old project-loader wrapper directly; they depend on the shared core facade.
- Market and financial router CLIs now have focused command surfaces instead of only `tushare-ping`.
- The true loader split is still not complete: `investment_system.core.project_loader` still delegates `ProjectConfig`, `load_project()`, and CLI behavior to the legacy loader, and the broad legacy runner may still import old pipeline modules.
- Future work should move `ProjectConfig`, validation flow, and Tushare implementation fully into core before any wrapper deletion is considered.

## 8. Validation Gates for Each Migration PR/Step

Minimum gate for any code movement:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe -m py_compile <touched .py files>
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.core.project_loader --project tech_ai_semiconductor --json
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py pipeline-readiness --project tech_ai_semiconductor
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py validate-outputs --project tech_ai_semiconductor
```

Additional gates by area:

| Area | Gate |
|---|---|
| Evidence modules | evidence bindings, evidence schema, target-sector evidence coverage |
| Writer modules | candidate generation, candidate gate, no formal-root writes |
| Publish modules | publish gate dry-run, no-overwrite, hash checks, forbidden artifact absence |
| Data-source modules | source health checks, Tushare ping when relevant, no token leakage |
| Skill metadata | quick validation of each changed `SKILL.md` and referenced files |

## 9. Main Risks

| Risk | Why it matters | Mitigation |
|---|---|---|
| Import-path breakage | direct skill modules need project-local skill `src/` paths in subprocesses | use `skill_subprocess_env()` and keep wrapper modules until compatibility gates pass |
| duplicated project semantics | each skill may drift on paths/schema/evidence binding | centralize shared core |
| hidden writes | skill CLIs may obscure whether a command writes output | default to dry-run/preview; explicit write flags |
| stale docs and command snippets | many skills and references mention old pipeline commands | update references only after each CLI exists |
| formal output contamination | candidate/publish migration may write formal root unexpectedly | preserve stage policy and publish gates |
| historical audit reproducibility | older audit files include old commands | do not rewrite historical audit files |
| over-splitting | one file per skill command can create needless fragmentation | split by stable business responsibility, not by current filename alone |
| legacy broad runner complexity | `run_research.py` mixes market, financial, evidence, writer behavior | migrate last, keep as wrapper until stage flow replaces it |

## 10. Working Checklist

- [x] Phase 0 baseline captured.
- [x] `investment_system/core/` created.
- [ ] `load_project.py` split into core modules with old wrapper preserved.
- [x] Skill CLI wrappers added for all seven project-local skills.
- [x] `evidence-miner` logic migrated.
- [x] `quality-auditor` gate logic migrated.
- [x] `research-writer` candidate generation migrated.
- [x] `sector-research-orchestrator` stage/publish orchestration migrated.
- [x] Market/financial data wrappers migrated.
- [x] Forecast normalization module implemented or explicitly deferred.
- [x] `workflow_stages.yaml` switched to skill CLI routing.
- [x] `AGENTS.md`, README, and skill references updated.
- [x] Compatibility wrappers audited.
- [x] Legacy cleanup decision made separately.
- [x] Internal subprocess calls switched to skill/core module names.

## 11. Update Rules for This File

- Update this file before each migration phase starts.
- Add actual command outputs or audit links after each phase completes.
- Mark a row as migrated only after both the new skill CLI and the old compatibility command pass.
- Do not record mock, preview, or dry-run artifacts as formal research output.
- Do not use this file to authorize deletion; cleanup needs a separate explicit deletion list and user confirmation.
