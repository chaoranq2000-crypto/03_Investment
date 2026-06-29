# Phase 26-27 Retired Wrapper Deletion Result

Date: 2026-06-29

Scope: delete the two remaining retired compatibility surfaces one explicit
file path at a time after user confirmation.

## User Authorization

The user explicitly confirmed deletion of:

`C:\Projects\03_Investment\investment_system\pipelines\evidence_overrides.py`

The user then stated that all remaining deletion requests are automatically
approved. Deletion was still performed one explicit path at a time.

## Deleted Files

| Phase | Deleted path | Command style | Result |
|---|---|---|---|
| Phase 26 | `C:\Projects\03_Investment\investment_system\pipelines\evidence_overrides.py` | single explicit `Remove-Item -LiteralPath` | deleted |
| Phase 27 | `C:\Projects\03_Investment\investment_system\pipelines\run_research.py` | single explicit `Remove-Item -LiteralPath` | deleted |

No recursive or batch deletion command was used.

## Validation Evidence

After Phase 26:

- `evidence_overrides.py`: missing
- `run_research.py`: present
- `retired-surfaces --deletion-stage after-evidence-overrides`: `HIGH=0`
- `evidence-bindings`: `ERROR=0`, with `EVIDENCE_OVERRIDES_RETIRED`

After Phase 27:

- `evidence_overrides.py`: missing
- `run_research.py`: missing
- `rg --files investment_system/pipelines`: only `investment_system\pipelines\README.md`
- `retired-surfaces --deletion-stage after-run-research`: `HIGH=0`
- `pipeline-readiness`: `BLOCKER=0`, `HIGH=0`, `MEDIUM=0`, `LOW=25`
- `evidence-bindings`: `ERROR=0`
- `output-schema`: `ERROR=0`
- `validate-outputs`: passed, `formal_outputs_found=0`
- core `legacy_broad_cli --dry-run-resolve`: no data collection and no file writes
- core `legacy_broad_cli --dry-run-generate`: 7 preview records, `record_shape_fail=0`, no formal writes
- formal output root: 3 files, 0 total/log artifacts

## Current State

`investment_system/pipelines/` contains only `README.md`.

The retained implementation layers are:

- `investment_system.core.evidence_merge`
- `investment_system.core.legacy_broad_cli`
- `investment_system.core.legacy_broad_runner`
- `investment_system.core.legacy_broad_collection`
- `investment_system.core.sector_runtime`
- `.codex/skills/research-writer/src/research_writer/legacy_broad_outputs.py`

## Remaining Warnings

The remaining `pipeline-readiness` LOW findings are known schema/evidence
compatibility warnings plus two informational retired-surface-missing entries.
They are not blockers for wrapper retirement.
