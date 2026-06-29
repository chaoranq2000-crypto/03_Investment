# Phase 18 Active Legacy Dependency Audit

Date: 2026-06-29

Scope:

- `investment_system/pipelines/run_research.py`
- `investment_system/pipelines/evidence_overrides.py`
- references to `investment_system.core.legacy_broad_cli`

Search commands:

```powershell
rg -n "investment_system\.pipelines\.run_research|pipelines\.run_research|python -m investment_system\.pipelines\.run_research|investment_system\\pipelines\\run_research.py|investment_system/pipelines/run_research.py|run_research\.py" --hidden -g "!.git/**" -g "!investment_system/data/**" -g "!科技主线调研输出/**"
rg -n "investment_system\.pipelines\.evidence_overrides|pipelines\.evidence_overrides|from evidence_overrides|import evidence_overrides|investment_system\\pipelines\\evidence_overrides.py|investment_system/pipelines/evidence_overrides.py|evidence_overrides\.py" --hidden -g "!.git/**" -g "!investment_system/data/**" -g "!科技主线调研输出/**"
rg -n "investment_system\.core\.legacy_broad_cli|-m investment_system\.core\.legacy_broad_cli|legacy_broad_cli" AGENTS.md investment_system .codex\skills -g "*.md" -g "*.py" -g "*.yaml"
```

## Current State

| Surface | Current role | Active dependency status | Deletion status |
|---|---|---|---|
| `investment_system/pipelines/run_research.py` | Compatibility forwarding entrypoint to `investment_system.core.legacy_broad_cli.main` | No active implementation dependency found. Active operator guidance now points to `investment_system.core.legacy_broad_cli`; historical records still mention the old path. | Candidate only after explicit user confirmation. |
| `investment_system/pipelines/evidence_overrides.py` | Compatibility wrapper around `investment_system.core.evidence_merge` | No active project-aware registry dependency found. Quality-auditor still scans it to ensure it remains wrapper/legacy-only. | Candidate only after explicit user confirmation. |
| `investment_system.core.legacy_broad_cli` | Retained legacy broad-runner implementation | Active compatibility implementation for broad generation when explicitly requested. | Keep. |

## Active References Kept Intentionally

| Reference | Reason |
|---|---|
| `.codex/skills/quality-auditor/src/quality_auditor/pipeline_readiness.py` | Scans both the pipeline wrapper and core CLI so future regressions are visible. |
| `.codex/skills/quality-auditor/src/quality_auditor/evidence_bindings.py` | Verifies `evidence_overrides.py` remains a compatibility wrapper around `investment_system.core.evidence_merge`. |
| `.codex/skills/quality-auditor/src/quality_auditor/output_schema.py` | Includes the pipeline path in a legacy-path scan; current wrapper has no hardcoded output path literals. |
| `.codex/skills/*/SKILL.md` and orchestrator references | Updated in Phase 18 to describe the core CLI as implementation and old pipeline file as compatibility-only. |

## Historical References Not Treated As Active Dependencies

- Prior phase records inside `skill_module_refactor_plan.md`.
- Prior audit reports under `investment_system/research/projects/tech_ai_semiconductor/audits/`.
- `run_manifest.yaml` comments that document the old `evidence_overrides.py` migration.
- Legacy prose embedded in `investment_system.core.evidence_merge` output text retained for reproducibility.

## Interpretation

- The legacy broad runner implementation has been fully moved out of `investment_system/pipelines/run_research.py`.
- The remaining pipeline file is deletable from an implementation perspective, but deletion is not authorized in Phase 18.
- `evidence_overrides.py` is also deletable from an implementation perspective after quality-auditor confirms wrapper status, but deletion is not authorized in Phase 18.
- Before deletion, request explicit confirmation for each file path and delete one file at a time only.

## Recommended Next Step

If the user confirms cleanup, delete candidates one explicit path at a time:

1. `investment_system/pipelines/evidence_overrides.py`
2. `investment_system/pipelines/run_research.py`

After each deletion, run syntax/import checks, `quality-auditor pipeline-readiness`, `quality-auditor validate-outputs`, and formal-root safety checks.
