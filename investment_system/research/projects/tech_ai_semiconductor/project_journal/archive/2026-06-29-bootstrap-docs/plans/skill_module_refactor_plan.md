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
| `investment_system/pipelines/evidence_overrides.py` | wrapper | shared core plus evidence/writer/forecast skills | `investment_system/core/evidence_merge.py` | Phase 12 compatibility wrapper only; no active project-aware registry role | deletion candidate after explicit confirmation |
| `investment_system/pipelines/run_research.py` | wrapper | legacy broad runner split across core/skills | `investment_system/core/legacy_broad_cli.py` plus lower core/skill modules | Phase 17 compatibility forwarding entrypoint only | deletion candidate after active dependency audit and explicit confirmation |

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

### Phase 9: Make Core Project Loader the Implementation Source

Goal: complete the true project-loader split by making `investment_system.core.project_loader` own `ProjectConfig`, validation flow, helper exports, and CLI behavior while preserving the old pipeline module as a compatibility wrapper.

- move the full project-loader implementation into `investment_system/core/project_loader.py`;
- use shared core constants for `WORKSPACE_ROOT`, `PROJECTS_ROOT`, and `SCHEMAS_ROOT` after the move;
- replace `investment_system/pipelines/sector_research/load_project.py` with a compatibility wrapper that re-exports the core implementation and forwards `main()`;
- update `investment_system/pipelines/run_research.py` internal imports to use `investment_system.core.project_loader`;
- keep old `python -m investment_system.pipelines.sector_research.load_project ...` commands runnable;
- do not delete wrappers or write formal outputs.

Phase 9 completion snapshot:

| Check | Result | Notes |
|---|---|---|
| Loader implementation source moved | done | `investment_system.core.project_loader` now owns `ProjectConfig`, `load_project()`, validation flow, dry-run path printing, and CLI behavior. |
| Legacy loader wrapper preserved | done | `investment_system/pipelines/sector_research/load_project.py` re-exports core loader globals and forwards `main()` for old commands/imports. |
| Broad runner imports updated | done | `investment_system/pipelines/run_research.py` now imports project-loader helpers from `investment_system.core.project_loader` or `investment_system.core.project_loader` module alias. |
| Old loader path dependency search | exit code 1/no matches | No Python file under `investment_system` or `.codex/skills` imports `investment_system.pipelines.sector_research.load_project` or `sector_research import load_project`. |
| Core and legacy loader smoke tests | warning-only parity | Core and legacy JSON commands both returned the baseline warning-only shape; legacy dry-run path command still resolved paths without writes. |
| Syntax checks | exit code 0 | `py_compile` passed for `investment_system/core/project_loader.py`, legacy loader wrapper, and `investment_system/pipelines/run_research.py`. |
| Skill workflow validation | exit code 0 | `sector-research-orchestrator scope-check --project tech_ai_semiconductor --sector-id high_speed_copper_connector` returned `blocking_count=0`. |
| Project validation | exit code 0 | `quality-auditor pipeline-readiness` stayed `BLOCKER=0`, `HIGH=0`, `MEDIUM=0`, `LOW=26`; `quality-auditor validate-outputs` passed with `formal_outputs_found=0`. |
| Data-router smoke tests | exit code 0 | Market `daily-kline` and financial `profit` dry-runs resolved the first high-speed-copper target to `002475.SZ` without live fetch or writes. |
| Legacy broad runner smoke test | exit code 0 | `python -m investment_system.pipelines.run_research --help` loaded successfully after import updates. |

Phase 9 interpretation:

- The true project-loader split is complete for the active skill workflow and broad runner imports.
- The old pipeline loader path remains only as a compatibility wrapper for historical commands.
- Wrapper deletion is still not authorized; later cleanup should wait for a separate explicit deletion list and another validation cycle.
- Tushare implementation is still delegated through `investment_system.core.data_sources.tushare_client` to the legacy Tushare module and remains a future cleanup target.

### Phase 10: Move Tushare Implementation Into Core and Delete the Old Pipeline File

Goal: remove the last Tushare-specific implementation dependency from `investment_system/pipelines/` and delete the old file only after it is no longer imported by code.

- move the real Tushare Pro client implementation into `investment_system/core/data_sources/tushare_client.py`;
- keep `market-data-router` and `financial-data-router` Tushare diagnostics pointed at the core module;
- verify no Python code imports `investment_system.pipelines.tushare_client`;
- delete only the explicit file path `investment_system/pipelines/tushare_client.py`;
- update pipeline guidance and legacy-retention notes;
- do not edit historical evidence YAML text that records how older evidence was collected;
- do not write formal outputs.

Phase 10 completion snapshot:

| Check | Result | Notes |
|---|---|---|
| Core Tushare implementation moved | done | `investment_system.core.data_sources.tushare_client` now owns `ROOT`, `.env.local` loading, proxy clearing, `get_tushare_pro()`, and CLI `main()`. |
| Old Tushare import search before deletion | exit code 1/no matches | No Python file under `investment_system` or `.codex/skills` imported `investment_system.pipelines.tushare_client`. |
| Old pipeline file deleted | done | Deleted `investment_system/pipelines/tushare_client.py` as one explicit file path after user authorization. |
| Guidance updated | done | Updated `investment_system/pipelines/README.md` and the Phase 6 wrapper-retention note to record the Phase 10 removal. |
| Compile/import smoke test | exit code 0 | `py_compile` passed for the core Tushare module and data-source package; lightweight import confirmed `ROOT`, `.env.local`, proxy keys, and env flag handling. |
| Tushare CLI help | exit code 0 | `python -m investment_system.core.data_sources.tushare_client --help` worked without the prior runpy warning after lazy package exports were added. |
| Tushare live ping diagnostics | exit code 1, external credential issue | Market and financial router `tushare-ping` both reached the core module, printed `tushare_version=1.4.29`, bridge URL, and `proxy_disabled=True`, then returned `tushare_ping_status=failed` with `Token expired`. |
| Project validation | exit code 0 | `quality-auditor pipeline-readiness` stayed `BLOCKER=0`, `HIGH=0`, `MEDIUM=0`, `LOW=26`; `quality-auditor validate-outputs` passed with `formal_outputs_found=0`. |
| Formal root safety | passed | `科技主线调研输出/` remained 3 Markdown files; no total-table or log formal outputs were generated. |
| Diff check | exit code 0 | `git diff --check` reported no whitespace errors; Git still printed LF-to-CRLF normalization warnings. |

Phase 10 interpretation:

- Tushare diagnostics and data-source access now route through the core data-source module without a pipeline implementation dependency.
- The old `investment_system/pipelines/tushare_client.py` compatibility file is gone by explicit user authorization.
- Live Tushare credentials are not currently usable: both skill pings returned `Token expired` after reaching the configured bridge.
- Historical evidence files may still mention the old collection path in source notes; those records were not rewritten.
- Remaining pipeline cleanup should focus on broad runner decomposition and wrapper retention/deletion decisions, not Tushare.

### Phase 11: Remove Migrated Pipeline Compatibility Wrappers

Goal: remove migrated `investment_system/pipelines/sector_research/*.py` compatibility wrappers and the root `investment_system/pipelines/validate_outputs.py` wrapper after the active workflow no longer depends on them.

- switch `workflow_stages.yaml` to skill-CLI-only routing and remove stored `compatibility_cli` commands;
- update `run_research.py` to import writer helpers directly from the `research-writer` skill module rather than the old `sector_research/output_writers.py` wrapper;
- delete only confirmed old wrapper files, one explicit file path at a time;
- keep `run_research.py` and `evidence_overrides.py` as retained legacy broad-runner surfaces;
- preserve historical audit records for reproducibility;
- do not delete directories recursively and do not write formal outputs.

Phase 11 completion snapshot:

| Check | Result | Notes |
|---|---|---|
| Workflow routing switched | done | `workflow_stages.yaml` now records `preferred_interface: skill_cli` and `compatibility_interface: removed_phase11`; stage entries no longer contain `compatibility_cli`. |
| Broad runner wrapper import removed | done | `investment_system/pipelines/run_research.py` now adds skill `src/` paths and imports `research_writer.output_writers` directly. |
| Migrated wrapper deletion | done | Deleted migrated wrappers under `investment_system/pipelines/sector_research/*.py` and `investment_system/pipelines/validate_outputs.py` one explicit file path at a time after user authorization. |
| Retained legacy surfaces | keep | `investment_system/pipelines/run_research.py` and `investment_system/pipelines/evidence_overrides.py` remain because broad generation has not been decomposed. |
| Guidance updated | done | Updated `AGENTS.md`, `investment_system/pipelines/README.md`, and the Phase 6 wrapper-retention note to document the Phase 11 removal. |
| Historical audit records | preserved | Older audit files may still mention old pipeline commands as historical evidence; they were not rewritten. |
| Syntax/help checks | exit code 0 | `py_compile` passed for touched Python files and `python -m investment_system.pipelines.run_research --help` loaded successfully. |
| Workflow validation | exit code 0 | `sector-research-orchestrator scope-check --project tech_ai_semiconductor --sector-id high_speed_copper_connector` returned `blocking_count=0`. |
| Project validation | exit code 0 | `quality-auditor pipeline-readiness` returned `BLOCKER=0`, `HIGH=0`, `MEDIUM=0`, `LOW=26`; `quality-auditor validate-outputs` passed with `formal_outputs_found=0`. |
| Formal root safety | passed | `科技主线调研输出/` remained 3 Markdown files; no total-table or log formal outputs were generated. |
| Diff check | exit code 0 | `git diff --check` reported no whitespace errors; Git still printed LF-to-CRLF normalization warnings. |

Phase 11 interpretation:

- The active project-aware workflow no longer depends on old sector-research pipeline wrappers.
- The remaining `investment_system/pipelines/` Python files are legacy broad-runner support, not migrated skill wrappers.
- Any future cleanup should decompose `run_research.py` first and should still use explicit path-by-path deletion only after a separate confirmation.

### Phase 12: Start Legacy Broad-Runner Decomposition

Goal: split the retained `run_research.py` and `evidence_overrides.py` responsibilities into stable core/skill import paths before making any deletion decision.

- move project-aware sector runtime helpers out of `run_research.py` into `investment_system.core.sector_runtime`;
- move legacy evidence merge helpers out of `evidence_overrides.py` into `investment_system.core.evidence_merge`;
- make `run_research.py` import sector runtime and evidence merge from core;
- downgrade `evidence_overrides.py` to a compatibility export wrapper only;
- update quality-auditor gates so Phase 12 core ownership is recognized;
- do not delete `run_research.py` or `evidence_overrides.py` in this phase;
- do not write formal outputs.

Phase 12 completion snapshot:

| Check | Result | Notes |
|---|---|---|
| Sector runtime core module | done | Added `investment_system/core/sector_runtime.py` for `SectorContext`, `ResearchRuntimePaths`, sector resolution, batch priority listing, coverage status, output-name safety, and path-template safety. |
| Evidence merge core module | done | Added `investment_system/core/evidence_merge.py` with the legacy curated-evidence merge helpers and explicit `LEGACY_ONLY_EVIDENCE_REGISTRY = True`. |
| Legacy evidence wrapper downgraded | done | `investment_system/pipelines/evidence_overrides.py` now re-exports `investment_system.core.evidence_merge` and no longer owns implementation logic. |
| Broad runner imports switched | done | `investment_system/pipelines/run_research.py` imports sector runtime and legacy evidence merge helpers from core. |
| Quality gates updated | done | `quality-auditor` now accepts `investment_system.core.sector_runtime` as the canonical sector-runtime implementation source and identifies `evidence_overrides.py` as a compatibility wrapper. |
| Deletion decision | deferred | `evidence_overrides.py` is now a deletion candidate, but deletion is not authorized in Phase 12. `run_research.py` still owns broad market/financial collection, table adapters, `DataTracker`, and write orchestration. |
| Syntax/help checks | exit code 0 | `py_compile` passed for touched Python files and `python -m investment_system.pipelines.run_research --help` loaded successfully. |
| Core import smoke test | exit code 0 | `sector_runtime` resolved `high_speed_copper_connector`, coverage returned `ok`, and `evidence_merge.load_theme_evidence("高速光模块")` loaded the legacy evidence mapping. |
| Legacy dry-run resolve | exit code 0 | `python -m investment_system.pipelines.run_research --project tech_ai_semiconductor --sector-id high_speed_copper_connector --dry-run-resolve` printed sector paths, stocks, and evidence bindings without writes. |
| Workflow validation | exit code 0 | `sector-research-orchestrator scope-check --project tech_ai_semiconductor --sector-id high_speed_copper_connector` returned `blocking_count=0`. |
| Project validation | exit code 0 | `quality-auditor pipeline-readiness` returned `BLOCKER=0`, `HIGH=0`, `MEDIUM=0`, `LOW=23`; `quality-auditor evidence-bindings` returned `ERROR=0`; `quality-auditor validate-outputs` passed with `formal_outputs_found=0`. |
| Formal root safety | passed | `科技主线调研输出/` remained 3 Markdown files; no total-table or log formal outputs were generated. |
| Diff check | exit code 0 | `git diff --check` reported no whitespace errors; Git still printed LF-to-CRLF normalization warnings. |

Phase 12 interpretation:

- `evidence_overrides.py` is no longer an implementation source; it is now only a compatibility surface.
- `run_research.py` is smaller but not yet deletable because it still owns the broad-runner execution path.
- The next decomposition slice should move market/financial collection and `DataTracker`/table adapters into skill/core modules or formally retire that broad path.

### Phase 13: Move Legacy Broad-Runner Writer Adapters Into Research Writer

Goal: continue decomposing `run_research.py` by moving legacy broad-runner output adapters and run logs into the `research-writer` skill module.

- add `research_writer.legacy_broad_outputs` as the implementation source for legacy company/comparison/source table field constants, CSV append helper, row adapters, and `DataTracker`;
- update `run_research.py` to import those writer helpers from `research_writer.legacy_broad_outputs`;
- make `DataTracker.save()` accept project config and runtime paths explicitly instead of reading `run_research.py` globals;
- update quality-auditor output-schema checks to read field constants from `research_writer.legacy_broad_outputs`;
- update retention notes and pipeline guidance;
- do not delete `run_research.py` or `evidence_overrides.py` in this phase;
- do not write formal outputs.

Phase 13 completion snapshot:

| Check | Result | Notes |
|---|---|---|
| Legacy writer adapter module | done | Added `.codex/skills/research-writer/src/research_writer/legacy_broad_outputs.py` for table field constants, CSV append, legacy-to-project row adapters, and `DataTracker`. |
| Broad runner imports switched | done | `investment_system/pipelines/run_research.py` now imports legacy table/log writer helpers from `research_writer.legacy_broad_outputs`. |
| Global coupling reduced | done | `DataTracker.save()` now receives project config and runtime paths explicitly from `run_research.py`. |
| Output-schema audit updated | done | `quality-auditor output-schema` now checks field constants in `research_writer.legacy_broad_outputs` instead of `run_research.py`. |
| Deletion decision | deferred | `run_research.py` remains necessary for market/financial collection and broad write orchestration. `evidence_overrides.py` remains a compatibility wrapper until deletion is explicitly confirmed. |
| Syntax/help checks | exit code 0 | `py_compile` passed for touched Python files and the legacy broad runner still loads. |
| Legacy dry-run resolve | exit code 0 | `python -m investment_system.pipelines.run_research --project tech_ai_semiconductor --sector-id high_speed_copper_connector --dry-run-resolve` printed sector paths, stocks, and evidence bindings without writes. |
| Project validation | exit code 0 | `quality-auditor output-schema` returned `ERROR=0`; `pipeline-readiness` returned `BLOCKER=0`, `HIGH=0`, `MEDIUM=0`, `LOW=23`; `validate-outputs` passed with `formal_outputs_found=0`. |
| Workflow validation | exit code 0 | `sector-research-orchestrator scope-check --project tech_ai_semiconductor --sector-id high_speed_copper_connector` returned `blocking_count=0`. |
| Formal root safety | passed | `科技主线调研输出/` remained 3 Markdown files; no total-table or log formal outputs were generated. |
| Diff check | exit code 0 | `git diff --check` reported no whitespace errors; Git still printed LF-to-CRLF normalization warnings. |

Phase 13 interpretation:

- Writer/log responsibilities are no longer implemented inside `run_research.py`.
- The remaining broad-runner decomposition target is market/financial collection plus orchestration side effects.
- If the broad-runner path is formally retired later, `evidence_overrides.py` can be considered for explicit path-by-path deletion first; `run_research.py` needs a larger replacement/retirement decision.

### Phase 14: Move Legacy Generated Row/Card Builders Into Research Writer

Goal: keep shrinking `run_research.py` by moving legacy broad-runner formatting, row-builder, scoring-text, and Markdown-card generation helpers into the research-writer skill module.

- move legacy market/financial formatting helpers such as percentage, amount, annual-profit selection, relative-strength placeholder, AKShare revenue derivation, source-id generation, and bubble-score text into `research_writer.legacy_broad_outputs`;
- move `build_company_rows()`, `build_comparison_row()`, and `build_research_card()` into `research_writer.legacy_broad_outputs`;
- keep `run_research.py` as the legacy broad-runner orchestration surface for now, with remaining responsibilities concentrated around cache reads/writes, API collection, runtime path setup, and CLI orchestration;
- update pipeline guidance and wrapper-retention notes;
- do not delete `run_research.py` or `evidence_overrides.py` in this phase;
- do not write formal outputs.

Phase 14 completion snapshot:

| Check | Result | Notes |
|---|---|---|
| Legacy row/card builders moved | done | `research_writer.legacy_broad_outputs` now owns generated company rows, comparison rows, score text, source IDs, financial formatting, and Markdown card construction. |
| Broad runner imports switched | done | `investment_system/pipelines/run_research.py` now imports these generated-output helpers from `research_writer.legacy_broad_outputs`. |
| Import cleanup | done | Removed unused `os`, `time`, `timedelta`, and `Optional` imports from `run_research.py`. |
| Deletion decision | deferred | `run_research.py` still owns API collection/cache writes and CLI orchestration. `evidence_overrides.py` remains a compatibility wrapper until deletion is explicitly confirmed. |
| Syntax/help checks | exit code 0 | `py_compile` passed for touched Python files and the legacy broad runner still loads. |
| Legacy dry-run resolve | exit code 0 | `python -m investment_system.pipelines.run_research --project tech_ai_semiconductor --sector-id high_speed_copper_connector --dry-run-resolve` printed sector paths, stocks, and evidence bindings without writes. |
| Project validation | exit code 0 | `quality-auditor output-schema` returned `ERROR=0`; `pipeline-readiness` returned `BLOCKER=0`, `HIGH=0`, `MEDIUM=0`, `LOW=23`; `validate-outputs` passed with `formal_outputs_found=0`. |
| Workflow validation | exit code 0 | `sector-research-orchestrator scope-check --project tech_ai_semiconductor --sector-id high_speed_copper_connector` returned `blocking_count=0`; one internal non-blocking step still reported `exit_code=3`. |
| Formal root safety | passed | `科技主线调研输出/` remained 3 Markdown files; no total-table or log formal outputs were generated. |
| Diff check | exit code 0 | `git diff --check` reported no whitespace errors; Git still printed LF-to-CRLF normalization warnings. |

Phase 14 interpretation:

- `run_research.py` is now primarily a legacy collection/orchestration shell.
- The next meaningful slice is to extract `read_raw_rows()`, `json_safe_rows()`, cache-path construction, BaoStock/Tencent/AKShare collection, and `run_sub_theme()` orchestration into a core or skill-level legacy collection adapter.
- After that, the legacy broad runner can be reduced to a thin CLI wrapper or formally retired if the skill flow covers the remaining use case.

### Phase 15: Move Legacy Market/Financial Collection Into Core

Goal: keep shrinking `run_research.py` by moving legacy broad-runner raw-cache helpers, run metadata writes, and BaoStock/Tencent/AKShare data collection into a core collection adapter.

- add `investment_system.core.legacy_broad_collection` as the implementation source for legacy raw-cache paths, raw-row reads, JSON-safe serialization, run metadata writes, market-data collection, profit collection, and AKShare revenue fallback handling;
- keep the existing raw cache layout under `investment_system/data/raw/<source>/<dataset>/<date>/`;
- preserve the old route behavior: cached rows first, BaoStock daily/profit via `ResearchClient`, Tencent direct fallback, optional Tencent-first daily mode, and AKShare financial indicator fallback when BaoStock annual revenue is absent;
- update `run_research.py` to call the core collection adapter and stop importing `ResearchClient`, `HumanRateLimiter`, `tencent_bar_direct`, `read_raw_rows()`, `json_safe_rows()`, `annual_profit()`, and `derive_revenue_yi_from_akshare_indicator()` directly;
- keep `run_research.py` as the legacy broad-runner CLI/orchestration surface for now, with remaining responsibilities concentrated around argument parsing, project-aware stock conversion, evidence/writer orchestration, and formal output writes;
- update pipeline guidance and wrapper-retention notes;
- do not delete `run_research.py` or `evidence_overrides.py` in this phase;
- do not write formal outputs.

Phase 15 completion snapshot:

| Check | Result | Notes |
|---|---|---|
| Legacy collection adapter | done | Added `investment_system.core.legacy_broad_collection` for collection paths, raw cache reads/writes, JSON-safe serialization, run metadata writes, market/profit collection, and AKShare revenue fallback. |
| Broad runner imports switched | done | `investment_system/pipelines/run_research.py` now calls `collect_legacy_market_financial_data()` and `write_run_metadata()` from core. |
| Direct data-source dependencies removed from runner | done | `run_research.py` no longer imports `ResearchClient`, `HumanRateLimiter`, or `tencent_bar_direct`; `load_env()` remains only for environment initialization. |
| Deletion decision | deferred | `run_research.py` still owns legacy CLI/project-aware orchestration and formal write behavior. `evidence_overrides.py` remains a compatibility wrapper until deletion is explicitly confirmed. |
| Syntax/help checks | exit code 0 | `py_compile` passed for `investment_system/core/legacy_broad_collection.py` and `run_research.py`; the legacy broad runner still loads. |
| Legacy collection smoke test | exit code 0 | `default_legacy_collection_paths()` and `json_safe_rows()` preserved the expected date/cache shapes without live data fetches or writes. |
| Legacy dry-run resolve | exit code 0 | `python -m investment_system.pipelines.run_research --project tech_ai_semiconductor --sector-id high_speed_copper_connector --dry-run-resolve` printed sector paths, stocks, and evidence bindings without writes. |
| Project validation | exit code 0 | `quality-auditor output-schema` returned `ERROR=0`; `pipeline-readiness` returned `BLOCKER=0`, `HIGH=0`, `MEDIUM=0`, `LOW=23`; `validate-outputs` passed with `formal_outputs_found=0`. |
| Workflow validation | exit code 0 | `sector-research-orchestrator scope-check --project tech_ai_semiconductor --sector-id high_speed_copper_connector` returned `blocking_count=0`; one internal non-blocking step still reported `exit_code=3`. |
| Formal root safety | passed | `科技主线调研输出/` remained 3 Markdown files; no total-table or log formal outputs were generated. |
| Diff check | exit code 0 | `git diff --check` reported no whitespace errors; Git still printed LF-to-CRLF normalization warnings. |

Phase 15 interpretation:

- Legacy market/financial data acquisition is no longer implemented in `run_research.py`.
- The next meaningful slice is to extract the remaining `run_sub_theme()` evidence/writer orchestration or reduce it to a thin call into a skill/core broad-runner adapter.
- `run_research.py` is closer to a CLI wrapper, but it is not yet deletable because it still decides project stock conversion, invokes evidence/writer steps, and writes formal outputs.

### Phase 16: Move Legacy Evidence/Writer Orchestration Into Core

Goal: remove the remaining `run_sub_theme()` implementation from `run_research.py` by moving legacy evidence loading, writer orchestration, formal write coordination, and result shaping into a core broad-runner adapter.

- add `investment_system.core.legacy_broad_runner` as the implementation source for legacy one-sector orchestration;
- move evidence loading/override application, missing-field tracking, row/card generation calls, formal CSV/Markdown/log write coordination, and legacy result-shape construction into `run_legacy_sub_theme()`;
- keep `run_research.py` as a thin legacy CLI wrapper for argument parsing, project loading, stock_universe conversion, batch/single-sector dispatch, tracker lifecycle, and result printing;
- keep `investment_system.core.legacy_broad_collection` as the market/financial collection adapter used by the broad runner;
- do not delete `run_research.py` or `evidence_overrides.py` in this phase;
- do not write formal outputs during validation.

Phase 16 completion snapshot:

| Check | Result | Notes |
|---|---|---|
| Legacy broad runner adapter | done | Added `investment_system.core.legacy_broad_runner` for one-sector legacy evidence/writer orchestration and formal write coordination. |
| Pipeline runner thinned | done | `investment_system/pipelines/run_research.py` no longer defines `run_sub_theme()` and now calls `run_legacy_sub_theme()`. |
| Direct evidence/writer orchestration removed from runner | done | `run_research.py` no longer imports evidence merge helpers or writer table/card builders directly; only `DataTracker` remains for tracker lifecycle/save. |
| Deletion decision | deferred | `run_research.py` still owns legacy CLI/project loading, stock conversion, single/batch dispatch, and result printing. `evidence_overrides.py` remains a compatibility wrapper until deletion is explicitly confirmed. |
| Syntax/help checks | exit code 0 | `py_compile` passed for `investment_system/core/legacy_broad_runner.py`, `legacy_broad_collection.py`, and `run_research.py`; the legacy broad runner CLI still loads. |
| Broad-runner import smoke test | exit code 0 | `run_legacy_sub_theme()` and `ensure_legacy_broad_dirs()` imported successfully with skill paths initialized. |
| Legacy dry-run resolve | exit code 0 | `python -m investment_system.pipelines.run_research --project tech_ai_semiconductor --sector-id high_speed_copper_connector --dry-run-resolve` printed sector paths, stocks, and evidence bindings without writes. |
| Runner implementation search | exit code 1/no matches | `run_research.py` no longer contains `run_sub_theme()` or direct calls/imports for evidence merge, writer builders, append CSV, collection, or run metadata helpers. |
| Project validation | exit code 0 | `quality-auditor output-schema` returned `ERROR=0`; `pipeline-readiness` returned `BLOCKER=0`, `HIGH=0`, `MEDIUM=0`, `LOW=23`; `validate-outputs` passed with `formal_outputs_found=0`. |
| Workflow validation | exit code 0 | `sector-research-orchestrator scope-check --project tech_ai_semiconductor --sector-id high_speed_copper_connector` returned `blocking_count=0`; one internal non-blocking step still reported `exit_code=3`. |
| Formal root safety | passed | `科技主线调研输出/` remained 3 Markdown files; no total-table or log formal outputs were generated. |
| Diff check | exit code 0 | `git diff --check` reported no whitespace errors; Git still printed LF-to-CRLF normalization warnings. |

Phase 16 interpretation:

- `run_research.py` is now a legacy CLI wrapper rather than an implementation owner for collection, evidence merge, writer adaptation, row/card generation, or formal write coordination.
- The next meaningful slice is to extract project stock conversion and batch/single-sector dispatch into a core CLI helper or formally replace this wrapper with the skill stage flow.
- Any retirement decision still needs an explicit compatibility audit showing no active workflow depends on `python -m investment_system.pipelines.run_research`.

### Phase 17: Move Legacy Broad CLI Into Core

Goal: make `investment_system/pipelines/run_research.py` a true compatibility forwarding entrypoint by moving CLI parsing, project loading, stock conversion, single/batch dispatch, tracker lifecycle, and result printing into core.

- add `investment_system.core.legacy_broad_cli` as the implementation source for the legacy broad-runner CLI;
- move `argparse` setup, `--dry-run-resolve`, `--dry-run-generate`, project-aware init, `stock_universe` to company-row conversion, single-sector dispatch, batch dispatch, tracker save lifecycle, and final result summary into the core CLI module;
- make `investment_system/pipelines/run_research.py` import and expose `investment_system.core.legacy_broad_cli.main` only, preserving historical `python -m investment_system.pipelines.run_research` compatibility;
- keep the core CLI directly executable with `python -m investment_system.core.legacy_broad_cli`;
- do not delete `run_research.py` or `evidence_overrides.py` in this phase;
- do not write formal outputs during validation.

Phase 17 completion snapshot:

| Check | Result | Notes |
|---|---|---|
| Legacy CLI module | done | Added `investment_system.core.legacy_broad_cli` for parser setup, dry-run modes, project loading, stock conversion, dispatch, tracker lifecycle, and result printing. |
| Pipeline runner wrapper | done | `investment_system/pipelines/run_research.py` now only prepares the historical import path and forwards `main` from `investment_system.core.legacy_broad_cli`. |
| Core CLI executable | done | `python -m investment_system.core.legacy_broad_cli --help` now runs the same CLI surface directly. |
| Deletion decision | deferred | `run_research.py` is a deletion candidate only after active dependency audit and explicit user confirmation. `evidence_overrides.py` remains a compatibility wrapper until deletion is explicitly confirmed. |
| Syntax/help checks | exit code 0 | `py_compile` passed for `legacy_broad_cli.py`, `legacy_broad_runner.py`, `legacy_broad_collection.py`, and the pipeline wrapper; both `python -m investment_system.pipelines.run_research --help` and `python -m investment_system.core.legacy_broad_cli --help` loaded. |
| Import forwarding smoke test | exit code 0 | `investment_system.pipelines.run_research.main is investment_system.core.legacy_broad_cli.main` returned `True`. |
| Core/wrapper dry-run resolve | exit code 0 | Both the pipeline wrapper and core CLI printed sector paths, stocks, and evidence bindings for `high_speed_copper_connector` without data collection or writes. |
| Generator dry-run | exit code 0 | `python -m investment_system.core.legacy_broad_cli --project tech_ai_semiconductor --sector-id high_speed_copper_connector --dry-run-generate` produced 7 preview records, `record_shape_fail=0`, and wrote no files. |
| Wrapper implementation search | exit code 1/no matches | `run_research.py` no longer contains parser, dispatch, stock conversion, `DataTracker`, or broad-runner implementation references. |
| Project validation | exit code 0 | `quality-auditor output-schema` returned `ERROR=0`; `pipeline-readiness` scanned 4 files and returned `BLOCKER=0`, `HIGH=0`, `MEDIUM=0`, `LOW=23`; `validate-outputs` passed with `formal_outputs_found=0`. |
| Workflow validation | exit code 0 | `sector-research-orchestrator scope-check --project tech_ai_semiconductor --sector-id high_speed_copper_connector` returned `blocking_count=0`; one internal non-blocking step still reported `exit_code=3`. |
| Formal root safety | passed | `科技主线调研输出/` remained 3 Markdown files; no total-table or log formal outputs were generated. |
| Diff check | exit code 0 | `git diff --check` reported no whitespace errors; Git still printed LF-to-CRLF normalization warnings. |

Phase 17 interpretation:

- `run_research.py` no longer owns legacy broad-runner behavior; it is now a compatibility surface.
- The remaining retirement work is an active dependency audit for callers of `investment_system.pipelines.run_research` and `investment_system.pipelines.evidence_overrides`, followed by explicit path-by-path deletion decisions.
- The live implementation path for the broad runner is now under `investment_system.core`, but this still does not mean formal outputs should be produced unless explicitly requested.

### Phase 18: Active Legacy Dependency Audit

Goal: prove whether remaining legacy compatibility surfaces are still active dependencies before any deletion request is considered.

- search active code, skill guidance, project configuration, and audit tooling for references to `investment_system.pipelines.run_research`, `investment_system/pipelines/run_research.py`, `investment_system.pipelines.evidence_overrides`, and `investment_system/pipelines/evidence_overrides.py`;
- update active skill guidance so it points to `investment_system.core.legacy_broad_cli` as the implementation path and treats `run_research.py` as compatibility-only;
- keep quality-auditor scans of the wrappers so future regressions are visible;
- document which remaining references are historical records, compatibility checks, or active guidance;
- do not delete `run_research.py` or `evidence_overrides.py` in this phase;
- do not write formal outputs during validation.

Phase 18 completion snapshot:

| Check | Result | Notes |
|---|---|---|
| Active dependency audit file | done | Added `audits/active_legacy_dependency_audit_phase18.md` with search commands, classifications, deletion candidates, and required next checks. |
| Skill guidance updated | done | Updated active skill guidance to point broad-runner implementation references at `investment_system.core.legacy_broad_cli`; `run_research.py` and `evidence_overrides.py` are described as compatibility-only. |
| Retention table refreshed | done | Updated the wrapper retention table and migration inventory so `run_research.py` and `evidence_overrides.py` reflect their current wrapper-only roles. |
| Active implementation dependency | none found | No current code path was found that needs `run_research.py` or `evidence_overrides.py` as implementation sources. Quality-auditor references are intentional wrapper checks. |
| Deletion decision | deferred | Both files are deletion candidates from an implementation perspective, but deletion still requires explicit user confirmation and one-path-at-a-time removal. |
| Syntax/no-write checks | exit code 0 | `py_compile` passed for core broad CLI/runner/collection, pipeline wrappers, and updated readiness audit; core and wrapper `--dry-run-resolve` printed paths without collection or writes; core `--dry-run-generate` produced 7 records with `record_shape_fail=0` and wrote no files. |
| Stale active guidance search | exit code 1/no matches | No active skill guidance still labels `investment_system/pipelines/run_research.py` as the standard pipeline or `evidence_overrides.py` as the implementation merge code. |
| Project validation | exit code 0 | `quality-auditor output-schema` returned `ERROR=0`; `pipeline-readiness` scanned 4 files and returned `BLOCKER=0`, `HIGH=0`, `MEDIUM=0`, `LOW=23`; `validate-outputs` passed with `formal_outputs_found=0`. |
| Evidence wrapper validation | exit code 0 | `quality-auditor evidence-bindings` returned `ERROR=0` and `EVIDENCE_OVERRIDES_COMPATIBILITY_WRAPPER`; remaining warnings are missing evidence coverage/legacy sector-id compatibility, not wrapper implementation dependency. |
| Workflow validation | exit code 0 | `sector-research-orchestrator scope-check --project tech_ai_semiconductor --sector-id high_speed_copper_connector` returned `blocking_count=0`; one internal non-blocking step still reported `exit_code=3`. |
| Formal root safety | passed | `科技主线调研输出/` remained 3 Markdown files; no total-table or log formal outputs were generated. |
| Diff check | exit code 0 | `git diff --check` reported no whitespace errors; Git still printed LF-to-CRLF normalization warnings. |

Phase 18 interpretation:

- `investment_system/pipelines/evidence_overrides.py` is the first low-risk deletion candidate because it is only a wrapper around `investment_system.core.evidence_merge`.
- `investment_system/pipelines/run_research.py` is also a deletion candidate because the implementation and active guidance now use `investment_system.core.legacy_broad_cli`.
- Do not delete either file without explicit user confirmation.

### Phase 19: Prepare Deletion-Safe Audit Gates

Goal: make the quality-auditor gates explain retired compatibility-surface deletion cleanly before any wrapper is removed.

- update `quality_auditor.pipeline_readiness` so missing retired compatibility surfaces are reported as `RETIRED_COMPATIBILITY_SURFACE_MISSING` instead of a generic missing audit target;
- update `quality_auditor.evidence_bindings` so a removed `evidence_overrides.py` is reported as `EVIDENCE_OVERRIDES_RETIRED` with project-aware evidence continuing through core/project manifests;
- keep active checks for existing wrappers in place until deletion actually happens;
- do not delete `run_research.py` or `evidence_overrides.py` in this phase;
- do not write formal outputs during validation.

Phase 19 completion snapshot:

| Check | Result | Notes |
|---|---|---|
| Readiness retired-surface handling | done | `pipeline_readiness.py` now classifies missing `run_research.py` or `evidence_overrides.py` as retired compatibility surfaces, not generic missing files. |
| Evidence wrapper retired handling | done | `evidence_bindings.py` now reports `EVIDENCE_OVERRIDES_RETIRED` if the compatibility wrapper is absent after deletion. |
| Deletion decision | deferred | No files deleted. Deletion still requires explicit user confirmation and one-path-at-a-time removal. |
| Syntax/no-write checks | exit code 0 | `py_compile` passed for updated quality-auditor modules plus current wrappers/core broad CLI; core and wrapper `--dry-run-resolve` printed paths without collection or writes; core `--dry-run-generate` produced 7 records with `record_shape_fail=0` and wrote no files. |
| Project validation | exit code 0 | `quality-auditor pipeline-readiness` returned `BLOCKER=0`, `HIGH=0`, `MEDIUM=0`, `LOW=23`; `output-schema` returned `ERROR=0`; `validate-outputs` passed with `formal_outputs_found=0`. |
| Evidence wrapper validation | exit code 0 | `quality-auditor evidence-bindings` returned `ERROR=0` and still reports `EVIDENCE_OVERRIDES_COMPATIBILITY_WRAPPER` while the wrapper remains present. |
| Workflow validation | exit code 0 | `sector-research-orchestrator scope-check --project tech_ai_semiconductor --sector-id high_speed_copper_connector` returned `blocking_count=0`; one internal non-blocking step still reported `exit_code=3`. |
| Formal root safety | passed | `科技主线调研输出/` remained 3 Markdown files; no total-table or log formal outputs were generated. |
| Diff check | exit code 0 | `git diff --check` reported no whitespace errors; Git still printed LF-to-CRLF normalization warnings. |

Phase 19 interpretation:

- The validation tools are now ready for the next step where wrapper files may be removed after explicit confirmation.
- This phase does not prove deletion has happened; it only prepares the gates to report deletion correctly when it is authorized.

### Phase 20: Confirmable Retired Wrapper Deletion Manifest

Goal: prepare an explicit deletion manifest for the final retired compatibility
surfaces without deleting them.

- record the exact current file sizes and SHA256 hashes for
  `investment_system/pipelines/evidence_overrides.py` and
  `investment_system/pipelines/run_research.py`;
- document the required one-file-at-a-time deletion order;
- document expected audit behavior after each file is removed;
- document the post-deletion validation gates;
- do not delete either file in this phase;
- do not write formal outputs during validation.

Phase 20 completion snapshot:

| Check | Result | Notes |
|---|---|---|
| Deletion manifest | done | Added `audits/retired_compatibility_deletion_manifest_phase20.md` with exact candidate paths, file sizes, hashes, deletion order, and validation gates. |
| Current candidate state | done | `evidence_overrides.py` is 907 bytes with SHA256 `420F144E11B49330DC80758EA44926AB46872898E04B9A1514ADBBB502512945`; `run_research.py` is 640 bytes with SHA256 `632A1FD848CC4D5E98C917BB0D2925ABE3086604EDFE2BF42D99B7A02FA8DF38`. |
| Deletion decision | deferred | No files deleted. Deletion still requires explicit confirmation for each exact path. |

Phase 20 interpretation:

- The two remaining retired compatibility wrappers are now ready for a controlled
  deletion decision, but the repository state is still no-delete.
- The first deletion candidate is `investment_system/pipelines/evidence_overrides.py`;
  the second is `investment_system/pipelines/run_research.py` after validation.

### Phase 21: Retired Surface Readiness Audit Command

Goal: turn the Phase 20 manual deletion manifest into a reusable read-only audit
gate that can be run both before and after each single-path deletion.

- add a `quality-auditor retired-surfaces` command;
- verify registered retired compatibility surfaces are either thin wrappers or
  already absent;
- flag active Python imports of
  `investment_system.pipelines.run_research` or
  `investment_system.pipelines.evidence_overrides` as HIGH;
- keep the command read-only and safe to run before any deletion confirmation;
- do not delete either wrapper in this phase;
- do not write formal outputs during validation.

Phase 21 completion snapshot:

| Check | Result | Notes |
|---|---|---|
| Retired surface audit module | done | Added `quality_auditor.retired_surfaces` and exposed it through `.codex/skills/quality-auditor/scripts/cli.py retired-surfaces`. |
| Current retired-surface state | exit code 0 | `retired-surfaces --project tech_ai_semiconductor` returned `HIGH=0`, `LOW=0`, `INFO=5`: both registered surfaces are present and thin wrappers; no active Python imports of the retired modules were found. |
| Syntax check | pass with workaround | Direct `py_compile` hit Windows `__pycache__` write denial (`WinError 5`); an AST syntax check with `python -B` passed for the new module and command map. |
| Deletion decision | deferred | No files deleted. Deletion still requires explicit confirmation for each exact path. |

Phase 21 interpretation:

- The deletion readiness check is now executable rather than only documented.
- The repository remains in no-delete state, but the next deletion turn can use
  `retired-surfaces` as the first gate before removing
  `investment_system/pipelines/evidence_overrides.py`.

### Phase 22: Remove Retired Wrapper Paths from Active Skill Guidance

Goal: prevent active operator guidance from continuing to point humans at the
two retired wrapper file paths while preserving historical migration records.

- update active `.codex/skills/**/*.md` guidance so it points to
  `investment_system.core.evidence_merge`,
  `investment_system.core.legacy_broad_cli`, and
  `quality-auditor retired-surfaces`;
- extend `quality_auditor.retired_surfaces` so it fails with HIGH if active
  skill guidance reintroduces `investment_system/pipelines/run_research.py` or
  `investment_system/pipelines/evidence_overrides.py`;
- keep historical audit files and this refactor plan unchanged as migration
  evidence except for current phase records;
- do not delete either wrapper in this phase;
- do not write formal outputs during validation.

Phase 22 completion snapshot:

| Check | Result | Notes |
|---|---|---|
| Active skill guidance updated | done | Removed retired wrapper file paths from active skill guidance under `.codex/skills/**/*.md`; guidance now points to core implementations and `quality-auditor retired-surfaces`. |
| Retired surface audit hardened | done | `quality_auditor.retired_surfaces` now checks active Python imports and active skill Markdown guidance. |
| Active guidance search | exit code 1/no matches | `rg` found no `investment_system/pipelines/run_research.py` or `investment_system/pipelines/evidence_overrides.py` references under active `.codex/skills/**/*.md`. |
| Retired surface validation | exit code 0 | `retired-surfaces --project tech_ai_semiconductor` returned `HIGH=0`, `LOW=0`, `INFO=6`, including `NO_ACTIVE_GUIDANCE_RETIRED_PATHS`. |
| Syntax check | exit code 0 | AST syntax check with `python -B` passed for `quality_auditor.retired_surfaces`. |
| Deletion decision | deferred | No files deleted. Deletion still requires explicit confirmation for each exact path. |

Phase 22 interpretation:

- Active human-facing workflow guidance no longer names the retired wrapper file
  paths; the wrappers remain only as compatibility files and historical
  migration evidence.
- The next deletion phase can begin with
  `quality-auditor retired-surfaces` and then remove
  `investment_system/pipelines/evidence_overrides.py` only after explicit
  path confirmation.

### Phase 23: Legacy Pipeline Directory Boundary Gate

Goal: make the retired pipeline directory boundary executable so new
implementation files do not reappear under `investment_system/pipelines/`.

- extend `quality_auditor.retired_surfaces` to scan
  `investment_system/pipelines/` recursively;
- allow only `README.md` plus registered retired compatibility surfaces until
  explicit deletion;
- ignore `__pycache__`;
- report any other file under `investment_system/pipelines/` as
  `UNREGISTERED_PIPELINE_SURFACE` with HIGH severity;
- do not delete either wrapper in this phase;
- do not write formal outputs during validation.

Phase 23 completion snapshot:

| Check | Result | Notes |
|---|---|---|
| Pipeline directory inventory | done | `rg --files investment_system/pipelines` shows only `README.md`, `evidence_overrides.py`, and `run_research.py`. |
| Retired surface audit hardened | done | `quality_auditor.retired_surfaces` now checks the pipeline directory boundary in addition to wrapper thinness, active imports, and active skill guidance. |
| Retired surface validation | exit code 0 | `retired-surfaces --project tech_ai_semiconductor` returned `HIGH=0`, `LOW=0`, `INFO=7`, including `PIPELINE_DIRECTORY_BOUNDARY_OK`. |
| Syntax check | exit code 0 | AST syntax check with `python -B` passed for `quality_auditor.retired_surfaces`. |
| Deletion decision | deferred | No files deleted. Deletion still requires explicit confirmation for each exact path. |

Phase 23 interpretation:

- The legacy pipeline directory is now guarded against new unregistered
  implementation files.
- The only remaining files under `investment_system/pipelines/` are README plus
  the two registered retired compatibility surfaces awaiting explicit
  path-by-path deletion.

### Phase 24: Deletion Stage State Gate

Goal: make the remaining one-file-at-a-time deletion sequence mechanically
verifiable at each step.

- extend `quality_auditor.retired_surfaces` with `--deletion-stage`;
- support `no-delete`, `after-evidence-overrides`, and `after-run-research`;
- report a HIGH `RETIRED_SURFACE_STAGE_MISMATCH` if a wrapper's actual
  present/missing state does not match the selected stage;
- keep the command read-only;
- do not delete either wrapper in this phase;
- do not write formal outputs during validation.

Phase 24 completion snapshot:

| Check | Result | Notes |
|---|---|---|
| Deletion-stage argument | done | `quality-auditor retired-surfaces` now accepts `--deletion-stage no-delete|after-evidence-overrides|after-run-research`. |
| Current stage validation | exit code 0 | `retired-surfaces --deletion-stage no-delete` returned `HIGH=0`, `LOW=0`, `INFO=9`: both remaining retired wrappers present as expected. |
| Stage mismatch validation | expected exit code 1 | `retired-surfaces --deletion-stage after-evidence-overrides` returned `RETIRED_SURFACE_STAGE_MISMATCH` because `evidence_overrides.py` is still present before deletion. |
| Deletion decision | deferred | No files deleted. Deletion still requires explicit confirmation for each exact path. |

Phase 24 interpretation:

- The next deletion turn can verify the pre-delete state with
  `--deletion-stage no-delete`.
- After deleting only `investment_system/pipelines/evidence_overrides.py`, the
  matching gate becomes `--deletion-stage after-evidence-overrides`.
- After deleting `investment_system/pipelines/run_research.py`, the matching
  gate becomes `--deletion-stage after-run-research`.

### Phase 25: Pre-Delete Readiness Certificate

Goal: record the authoritative current-state evidence that the two remaining
retired wrappers are technically ready for explicit one-file-at-a-time deletion.

- capture the current `investment_system/pipelines/` file inventory;
- capture `retired-surfaces --deletion-stage no-delete --json` evidence;
- capture the formal output boundary check;
- identify the exact first deletion candidate;
- do not delete either wrapper in this phase;
- do not write formal outputs during validation.

Phase 25 completion snapshot:

| Check | Result | Notes |
|---|---|---|
| Pre-delete readiness file | done | Added `audits/retired_wrapper_predelete_readiness_phase25.md`. |
| Pipeline inventory | done | `investment_system/pipelines/` contains only README plus the two registered retired compatibility surfaces. |
| Retired surface stage | exit code 0 | `retired-surfaces --deletion-stage no-delete --json` returned `HIGH=0`, `LOW=0`, `INFO=9`. |
| Formal output boundary | passed | Formal root still has 3 files and 0 total/log artifacts. |
| Deletion decision | deferred | No files deleted. Deletion still requires explicit confirmation for each exact path. |

Phase 25 interpretation:

- Technical readiness for deleting the first retired wrapper is proven by the
  current audit gates.
- The next step is not more decomposition; it is explicit confirmation for
  `C:\Projects\03_Investment\investment_system\pipelines\evidence_overrides.py`.

### Phase 26-27: Delete Remaining Retired Compatibility Surfaces

Goal: remove the last two retired compatibility wrappers one explicit file path
at a time after user confirmation.

- delete `investment_system/pipelines/evidence_overrides.py` first;
- validate `--deletion-stage after-evidence-overrides`;
- delete `investment_system/pipelines/run_research.py` second after the user
  approved remaining deletion requests;
- validate `--deletion-stage after-run-research`;
- keep active implementation under `investment_system/core/`;
- do not write formal outputs during validation.

Phase 26-27 completion snapshot:

| Check | Result | Notes |
|---|---|---|
| Deletion result file | done | Added `audits/retired_wrapper_deletion_result_phase26_27.md`. |
| Evidence wrapper deletion | done | Deleted `investment_system/pipelines/evidence_overrides.py` with one explicit `Remove-Item -LiteralPath`; `after-evidence-overrides` gate returned `HIGH=0`. |
| Broad runner wrapper deletion | done | Deleted `investment_system/pipelines/run_research.py` with one explicit `Remove-Item -LiteralPath`; `after-run-research` gate returned `HIGH=0`. |
| Pipeline directory boundary | done | `rg --files investment_system/pipelines` now lists only `investment_system\pipelines\README.md`. |
| Project validation | exit code 0 | `pipeline-readiness` returned `BLOCKER=0`, `HIGH=0`, `MEDIUM=0`; `evidence-bindings` returned `ERROR=0`; `output-schema` returned `ERROR=0`; `validate-outputs` passed with `formal_outputs_found=0`. |
| Core legacy broad CLI | exit code 0 | Core `--dry-run-resolve` and `--dry-run-generate` still work without data collection or formal writes; preview record shape failures remain 0. |
| Formal output boundary | passed | Formal root still has 3 files and 0 total/log artifacts. |

Phase 26-27 interpretation:

- The retired compatibility surfaces under `investment_system/pipelines/` are
  now removed.
- `investment_system/pipelines/` is no longer an implementation layer; it only
  retains README guidance.
- The stable implementation surface for the legacy broad runner is now
  `investment_system/core/` plus the `research-writer` skill helper module.

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
- [x] `load_project.py` split into core modules with old wrapper preserved.
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
- [x] Tushare implementation moved into core and old pipeline file deleted.
- [x] Migrated sector-research pipeline wrappers removed after explicit Phase 11 authorization.
- [x] Legacy broad-runner decomposition started: sector runtime and evidence merge moved into core.
- [x] Legacy broad-runner writer adapters and DataTracker moved into research-writer skill.
- [x] Legacy broad-runner generated row/card builders moved into research-writer skill.
- [x] Legacy broad-runner market/financial collection and cache handling moved into core.
- [x] Legacy broad-runner evidence/writer orchestration moved into core.
- [x] Legacy broad-runner CLI wrapper moved into core.
- [x] Active legacy dependency audit completed for remaining compatibility surfaces.
- [x] Quality-auditor gates prepared for retired compatibility-surface deletion.
- [x] Retired compatibility wrapper deletion manifest prepared without deletion.
- [x] Retired compatibility wrapper readiness audit command added.
- [x] Active skill guidance no longer points at retired wrapper file paths.
- [x] Legacy pipeline directory boundary gate added.
- [x] Deletion-stage state gate added for remaining retired wrappers.
- [x] Pre-delete readiness certificate captured for remaining retired wrappers.
- [x] Remaining retired compatibility surfaces deleted one explicit path at a time.

## 11. Update Rules for This File

- Update this file before each migration phase starts.
- Add actual command outputs or audit links after each phase completes.
- Mark a row as migrated only after both the new skill CLI and the old compatibility command pass.
- Do not record mock, preview, or dry-run artifacts as formal research output.
- Do not use this file to authorize deletion; cleanup needs a separate explicit deletion list and user confirmation.
