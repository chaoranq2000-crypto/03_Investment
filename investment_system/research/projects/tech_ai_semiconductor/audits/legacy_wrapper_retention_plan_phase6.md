# Phase 6 Legacy Wrapper Retention Plan

project_id: `tech_ai_semiconductor`
date: `2026-06-28`
scope: migration cleanup decision only
formal_output_write: `false`

## Decision

No legacy pipeline file should be deleted in Phase 6.

The skill CLIs are now the preferred operator-facing entry points, but legacy
`investment_system.pipelines.*` modules must stay in place until the next full
validation cycle and until loader/Tushare/broad-runner compatibility decisions
are made explicitly.

Deletion, if requested later, must be path-by-path with explicit user
confirmation. Do not use batch or recursive deletion.

## Keep Required

| Path | Reason |
|---|---|
| `investment_system/pipelines/sector_research/load_project.py` | Still the legacy CLI and compatibility surface for project loading; core facades delegate through it during the current split. |
| `investment_system/pipelines/run_research.py` | Legacy broad research runner; still the fallback only when broad generation is explicitly requested. |
| `investment_system/pipelines/evidence_overrides.py` | Legacy-only evidence adapter imported by `run_research.py`. |
| `investment_system/pipelines/tushare_client.py` | Current implementation behind `investment_system.core.data_sources.tushare_client`; keep until the real implementation moves fully into core. |
| `investment_system/pipelines/validate_outputs.py` | Compatibility wrapper for `quality_auditor.validate_outputs`; keep for old commands and one validation cycle after Phase 7. |

## Keep For One Validation Cycle

These files are migrated wrappers that re-export skill modules through
`investment_system.core.skill_module_loader.export_skill_module(...)`.
Keep them until internal callers are switched to direct skill/core modules and
one full validation cycle passes.

| Legacy wrapper | Delegates to |
|---|---|
| `investment_system/pipelines/sector_research/audit_dry_run_outputs.py` | `quality_auditor.dry_run_outputs` |
| `investment_system/pipelines/sector_research/audit_evidence_bindings.py` | `quality_auditor.evidence_bindings` |
| `investment_system/pipelines/sector_research/audit_evidence_coverage.py` | `quality_auditor.evidence_coverage` |
| `investment_system/pipelines/sector_research/audit_evidence_schema.py` | `quality_auditor.evidence_schema` |
| `investment_system/pipelines/sector_research/audit_formal_candidate_outputs.py` | `quality_auditor.candidate_outputs` |
| `investment_system/pipelines/sector_research/audit_formal_publish_readiness.py` | `quality_auditor.publish_readiness` |
| `investment_system/pipelines/sector_research/audit_formal_publish_result.py` | `quality_auditor.publish_result` |
| `investment_system/pipelines/sector_research/audit_gated_formal_outputs.py` | `quality_auditor.gated_outputs` |
| `investment_system/pipelines/sector_research/audit_generator_previews.py` | `quality_auditor.generator_previews` |
| `investment_system/pipelines/sector_research/audit_mock_outputs.py` | `quality_auditor.mock_outputs` |
| `investment_system/pipelines/sector_research/audit_output_schema.py` | `quality_auditor.output_schema` |
| `investment_system/pipelines/sector_research/audit_pipeline_readiness.py` | `quality_auditor.pipeline_readiness` |
| `investment_system/pipelines/sector_research/audit_stock_universe.py` | `quality_auditor.stock_universe` |
| `investment_system/pipelines/sector_research/build_dry_run_outputs.py` | `research_writer.dry_run_outputs` |
| `investment_system/pipelines/sector_research/build_evidence_skeleton.py` | `evidence_miner.draft_skeleton` |
| `investment_system/pipelines/sector_research/build_formal_candidate_outputs.py` | `research_writer.candidate_outputs` |
| `investment_system/pipelines/sector_research/build_mock_outputs.py` | `research_writer.mock_outputs` |
| `investment_system/pipelines/sector_research/collect_official_evidence.py` | `evidence_miner.source_manifest` |
| `investment_system/pipelines/sector_research/output_writers.py` | `research_writer.output_writers` |
| `investment_system/pipelines/sector_research/prepare_formal_publish.py` | `sector_research_orchestrator.publish` |
| `investment_system/pipelines/sector_research/promote_formal_candidate_outputs.py` | `sector_research_orchestrator.promote` |
| `investment_system/pipelines/sector_research/register_evidence_file.py` | `evidence_miner.register` |
| `investment_system/pipelines/sector_research/run_sector_stage.py` | `sector_research_orchestrator.stage_runner` |
| `investment_system/pipelines/sector_research/split_tushare_cache.py` | `evidence_miner.tushare_cache_split` |
| `investment_system/pipelines/sector_research/validate_curated_evidence.py` | `evidence_miner.curation_validator` |

## Blocking Dependencies Before Any Removal

- Phase 7 resolved nested subprocess calls in
  `sector_research_orchestrator.stage_runner`,
  `sector_research_orchestrator.publish`, and the quality-auditor
  candidate/publish/gated checks.
- Several skill modules still import project-loading helpers from
  `investment_system.pipelines.sector_research.load_project`; keep loader
  compatibility until the loader is truly split into core modules.
- `investment_system.core.data_sources.tushare_client` still delegates to
  `investment_system.pipelines.tushare_client`; keep the Tushare pipeline file
  until the implementation is moved fully into core.
- `run_research.py` and `evidence_overrides.py` remain the legacy broad-runner
  path and should be retained unless broad generation is decomposed.
- `workflow_stages.yaml` intentionally records legacy compatibility commands
  beside the preferred skill CLI commands.
- Historical audit files preserve old command lines for reproducibility and
  should not be rewritten as cleanup.

## Later Cleanup Preconditions

Before any explicit deletion request is safe:

1. Complete one full validation cycle after the Phase 7 internal subprocess
   migration.
2. Move the real Tushare implementation from `investment_system/pipelines/`
   into `investment_system/core/data_sources/`, then leave only a wrapper if
   needed.
3. Decide whether `run_research.py` remains as a legacy broad runner or is
   decomposed into skill-level flows.
4. Run the full non-formal chain through skill CLIs and one compatibility
   wrapper pass after the internal-call migration.
5. If deletion is requested, delete only one explicit file path at a time after
   confirmation.
