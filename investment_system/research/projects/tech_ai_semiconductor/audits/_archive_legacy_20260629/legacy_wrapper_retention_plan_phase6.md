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
| `investment_system/pipelines/run_research.py` | Phase 17 compatibility forwarding entrypoint around `investment_system.core.legacy_broad_cli`; no remaining implementation logic. Keep until active references are switched or deletion is explicitly confirmed. |
| `investment_system/pipelines/evidence_overrides.py` | Phase 12 compatibility wrapper around `investment_system.core.evidence_merge`; no active project-aware registry role. Keep until old imports are audited and deletion is explicitly confirmed. |

## Removed After Explicit Phase 10 Authorization

| Path | Phase 10 result |
|---|---|
| `investment_system/pipelines/tushare_client.py` | Deleted as one explicit file after the real implementation moved into `investment_system.core.data_sources.tushare_client` and code references to the old module were absent. |

## Removed After Explicit Phase 11 Authorization

These files had been migrated wrappers that re-exported skill modules through
`investment_system.core.skill_module_loader.export_skill_module(...)`. They
were deleted one explicit file at a time after internal callers were switched to
skill/core imports and `workflow_stages.yaml` stopped recording pipeline
compatibility commands.

| Removed wrapper | Replacement |
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
| `investment_system/pipelines/sector_research/load_project.py` | `investment_system.core.project_loader` |
| `investment_system/pipelines/sector_research/output_writers.py` | `research_writer.output_writers` |
| `investment_system/pipelines/sector_research/prepare_formal_publish.py` | `sector_research_orchestrator.publish` |
| `investment_system/pipelines/sector_research/promote_formal_candidate_outputs.py` | `sector_research_orchestrator.promote` |
| `investment_system/pipelines/sector_research/register_evidence_file.py` | `evidence_miner.register` |
| `investment_system/pipelines/sector_research/run_sector_stage.py` | `sector_research_orchestrator.stage_runner` |
| `investment_system/pipelines/sector_research/split_tushare_cache.py` | `evidence_miner.tushare_cache_split` |
| `investment_system/pipelines/sector_research/validate_curated_evidence.py` | `evidence_miner.curation_validator` |
| `investment_system/pipelines/validate_outputs.py` | `quality_auditor.validate_outputs` |

## Blocking Dependencies Before Any Removal

- Phase 7 resolved nested subprocess calls in
  `sector_research_orchestrator.stage_runner`,
  `sector_research_orchestrator.publish`, and the quality-auditor
  candidate/publish/gated checks.
- Phase 9 moved project loading into `investment_system.core.project_loader`;
  Phase 11 removed the old loader wrapper.
- Phase 10 moved `investment_system.core.data_sources.tushare_client` to a real
  implementation and removed `investment_system/pipelines/tushare_client.py`
  after explicit user authorization.
- Phase 12 moved `run_research.py` sector runtime helpers into
  `investment_system.core.sector_runtime` and legacy evidence merge helpers
  into `investment_system.core.evidence_merge`.
- Phase 13 moved legacy broad-runner table adapters, CSV append helper, and
  `DataTracker` into `research_writer.legacy_broad_outputs`.
- Phase 14 moved legacy broad-runner financial/market formatting helpers,
  company/comparison row builders, and Markdown card builder into
  `research_writer.legacy_broad_outputs`.
- Phase 15 moved legacy broad-runner raw-cache helpers, JSON-safe row
  serialization, run metadata writes, BaoStock/Tencent/AKShare collection, and
  financial fallback handling into `investment_system.core.legacy_broad_collection`.
- Phase 16 moved legacy broad-runner evidence/writer orchestration and formal
  CSV/Markdown/log write coordination into `investment_system.core.legacy_broad_runner`.
- Phase 17 moved legacy broad-runner CLI parsing, project loading,
  stock-universe conversion, single/batch dispatch, tracker lifecycle, and
  result printing into `investment_system.core.legacy_broad_cli`.
- Phase 18 found no active implementation dependency on
  `investment_system/pipelines/run_research.py` or
  `investment_system/pipelines/evidence_overrides.py`.
- Phase 19 prepared quality-auditor gates so missing retired compatibility
  surfaces are reported explicitly after deletion.
- Phase 20 added
  `investment_system/research/projects/tech_ai_semiconductor/audits/retired_compatibility_deletion_manifest_phase20.md`
  with exact paths, hashes, deletion order, and validation gates. No deletion
  was performed in Phase 20.
- Phase 21 added the read-only `quality-auditor retired-surfaces` command to
  verify both the no-delete wrapper state and the post-deletion retired-missing
  state.
- Phase 22 removed retired wrapper file paths from active skill guidance and
  extended `quality-auditor retired-surfaces` to fail if active skill guidance
  reintroduces those paths.
- Phase 23 extended `quality-auditor retired-surfaces` to fail if
  `investment_system/pipelines/` grows any unregistered file beyond README and
  registered retired compatibility surfaces.
- Phase 24 extended `quality-auditor retired-surfaces` with deletion-stage
  state checks for `no-delete`, `after-evidence-overrides`, and
  `after-run-research`.
- Phase 25 captured the pre-delete readiness certificate showing the remaining
  retired wrappers are technically ready for explicit one-file-at-a-time
  deletion.
- Phase 26 deleted `investment_system/pipelines/evidence_overrides.py` after
  explicit path confirmation.
- Phase 27 deleted `investment_system/pipelines/run_research.py` after the user
  approved the remaining deletion requests. Both deletions were performed one
  explicit path at a time.
- Phase 11 removed legacy compatibility commands from `workflow_stages.yaml`.
- Historical audit files preserve old command lines for reproducibility and
  should not be rewritten as cleanup.

## Later Cleanup Preconditions

Before any explicit deletion request is safe:

1. Complete one full validation cycle after the Phase 7 internal subprocess
   migration.
2. Completed in Phase 10: the real Tushare implementation moved from
   `investment_system/pipelines/` into `investment_system/core/data_sources/`;
   the old pipeline file was deleted as one explicit path.
3. Phase 12 started broad-runner decomposition by moving sector runtime helpers
   and legacy evidence merge into core.
4. Phase 13 moved table adapters, CSV append helper, and `DataTracker` into
   `research_writer.legacy_broad_outputs`.
5. Phase 14 moved generated row/card helpers into
   `research_writer.legacy_broad_outputs`.
6. Phase 15 moved legacy market/financial collection and cache handling into
   `investment_system.core.legacy_broad_collection`.
7. Phase 16 moved legacy evidence/writer orchestration and formal write
   coordination into `investment_system.core.legacy_broad_runner`.
8. Phase 17 moved legacy CLI parsing, project loading, stock conversion,
   single/batch dispatch, tracker lifecycle, and result printing into
   `investment_system.core.legacy_broad_cli`; `run_research.py` is now a
   compatibility forwarding entrypoint.
9. Phase 18 audited active references and found no active implementation
   dependency on `investment_system.pipelines.run_research` or
   `investment_system.pipelines.evidence_overrides`.
10. Phase 19 prepared audit gates for retired compatibility-surface deletion.
11. Phase 20 added the explicit retired-wrapper deletion manifest with exact
   paths, hashes, order, and post-deletion validation gates.
12. Phase 21 added a reusable read-only `retired-surfaces` audit command.
13. Phase 22 removed retired wrapper file paths from active skill guidance.
14. Phase 23 added the executable legacy pipeline directory boundary gate.
15. Phase 24 added the deletion-stage state gate for remaining retired wrappers.
16. Phase 25 captured the pre-delete readiness certificate.
17. Phase 26 deleted `investment_system/pipelines/evidence_overrides.py`.
18. Phase 27 deleted `investment_system/pipelines/run_research.py`.
19. Phase 11 removed the migrated wrapper set after skill CLI validation.
20. Future deletion requests should still delete only one explicit file path at
   a time after confirmation.
