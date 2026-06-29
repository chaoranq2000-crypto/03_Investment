# Phase 20 Retired Compatibility Deletion Manifest

Date: 2026-06-29 01:11:21 +08:00

Scope: prepare an explicit, one-file-at-a-time deletion manifest for the last
two retired compatibility surfaces. No deletion was performed in this phase.

This manifest does not authorize deletion by itself. Deletion still requires a
separate explicit user confirmation for the exact path being removed.

## Current Candidates

| Order | Path | Size | SHA256 | Current role | Deletion status |
|---|---:|---:|---|---|---|
| 1 | `investment_system/pipelines/evidence_overrides.py` | 907 bytes | `420F144E11B49330DC80758EA44926AB46872898E04B9A1514ADBBB502512945` | Compatibility exports for `investment_system.core.evidence_merge` | Candidate only; not deleted |
| 2 | `investment_system/pipelines/run_research.py` | 640 bytes | `632A1FD848CC4D5E98C917BB0D2925ABE3086604EDFE2BF42D99B7A02FA8DF38` | Compatibility entrypoint forwarding to `investment_system.core.legacy_broad_cli` | Candidate only; not deleted |

## Required Deletion Order

Run only after explicit user confirmation. Delete one exact path, then run the
validation gates before considering the next path.

1. Evidence wrapper:

```powershell
Remove-Item "C:\Projects\03_Investment\investment_system\pipelines\evidence_overrides.py"
```

Expected audit behavior after this deletion:

- `quality-auditor evidence-bindings` should report
  `EVIDENCE_OVERRIDES_RETIRED` as informational context.
- `quality-auditor pipeline-readiness` may report
  `RETIRED_COMPATIBILITY_SURFACE_MISSING` at LOW severity.

2. Legacy broad-runner wrapper:

```powershell
Remove-Item "C:\Projects\03_Investment\investment_system\pipelines\run_research.py"
```

Expected audit behavior after this deletion:

- `quality-auditor pipeline-readiness` may report
  `RETIRED_COMPATIBILITY_SURFACE_MISSING` at LOW severity.
- The supported no-write broad-runner entrypoint remains:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.core.legacy_broad_cli --project tech_ai_semiconductor --sector-id high_speed_copper_connector --dry-run-resolve
```

## Post-Deletion Validation Gates

Run after each single-path deletion:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe -m py_compile .codex\skills\quality-auditor\src\quality_auditor\pipeline_readiness.py .codex\skills\quality-auditor\src\quality_auditor\evidence_bindings.py investment_system\core\legacy_broad_cli.py investment_system\core\legacy_broad_runner.py investment_system\core\legacy_broad_collection.py investment_system\core\evidence_merge.py
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.core.legacy_broad_cli --help
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.core.legacy_broad_cli --project tech_ai_semiconductor --sector-id high_speed_copper_connector --dry-run-resolve
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.core.legacy_broad_cli --project tech_ai_semiconductor --sector-id high_speed_copper_connector --dry-run-generate
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py retired-surfaces --project tech_ai_semiconductor --deletion-stage <no-delete|after-evidence-overrides|after-run-research>
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py pipeline-readiness --project tech_ai_semiconductor
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py evidence-bindings --project tech_ai_semiconductor
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py output-schema --project tech_ai_semiconductor
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py validate-outputs --project tech_ai_semiconductor
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\sector-research-orchestrator\scripts\cli.py scope-check --project tech_ai_semiconductor --sector-id high_speed_copper_connector
git diff --check
```

Also verify the formal output root remains limited to sector-card Markdown files
and still has no `00_...` total table or `99_...` log artifacts.

## No-Delete Phase 20 Result

- `investment_system/pipelines/evidence_overrides.py`: still present.
- `investment_system/pipelines/run_research.py`: still present.
- No formal output generation requested.
- No file deletion performed.

## Phase 21 Automation Note

Phase 21 added the reusable read-only audit command:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py retired-surfaces --project tech_ai_semiconductor
```

Use this command before and after each single-path deletion. The expected
no-delete state is `HIGH=0` with both registered surfaces present as thin
wrappers, no active Python imports of the retired modules, and no active skill
guidance naming the retired wrapper file paths.

## Phase 22 Active Guidance Note

Phase 22 removed retired wrapper file paths from active `.codex/skills/**/*.md`
operator guidance. Active guidance now points to:

- `investment_system.core.evidence_merge` for evidence merge behavior;
- `investment_system.core.legacy_broad_cli` for the retained legacy broad-runner
  implementation;
- `quality-auditor retired-surfaces` for wrapper-retirement state checks.

Historical audit and refactor documents still preserve old path names as
migration evidence.

## Phase 23 Pipeline Directory Boundary Note

Phase 23 extended `quality-auditor retired-surfaces` so it also checks the
legacy pipeline directory boundary. The expected no-delete state is now:

- `investment_system/pipelines/README.md` is allowed;
- registered retired compatibility surfaces are allowed until explicit deletion:
  `evidence_overrides.py` and `run_research.py`;
- `__pycache__` files are ignored;
- any other file under `investment_system/pipelines/` is reported as
  `UNREGISTERED_PIPELINE_SURFACE` with HIGH severity.

This keeps `investment_system/core/` and skill modules as the stable
implementation layers and prevents new implementation files from reappearing in
the retired pipeline directory.

## Phase 24 Deletion Stage State Note

Phase 24 extended `quality-auditor retired-surfaces` with a deletion-stage
argument:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py retired-surfaces --project tech_ai_semiconductor --deletion-stage no-delete
```

Expected stages:

| Stage | `evidence_overrides.py` | `run_research.py` | Use case |
|---|---|---|---|
| `no-delete` | present | present | Current state before any remaining wrapper deletion. |
| `after-evidence-overrides` | missing | present | After explicitly deleting only `evidence_overrides.py`. |
| `after-run-research` | missing | missing | After explicitly deleting both retired wrappers one file at a time. |

Use the matching stage after each one-path deletion. A mismatch is reported as
`RETIRED_SURFACE_STAGE_MISMATCH` with HIGH severity.

## Phase 25 Pre-Delete Readiness Note

Phase 25 added:

`investment_system/research/projects/tech_ai_semiconductor/audits/retired_wrapper_predelete_readiness_phase25.md`

This file records the current no-delete evidence:

- `retired-surfaces --deletion-stage no-delete --json` returned `HIGH=0`;
- both remaining retired wrappers are present and thin;
- active Python imports and active skill guidance do not depend on the retired
  wrappers;
- the pipeline directory boundary contains only README plus registered retired
  compatibility surfaces;
- formal output root remains limited to 3 Markdown files with no total/log
  artifacts.

## Phase 26-27 Deletion Result Note

Phase 26 and Phase 27 completed the remaining retired wrapper deletion sequence:

- `investment_system/pipelines/evidence_overrides.py` deleted first.
- `investment_system/pipelines/run_research.py` deleted second.
- Both deletions used a single explicit file path.
- `retired-surfaces --deletion-stage after-run-research` returned `HIGH=0`.
- `investment_system/pipelines/` now contains only `README.md`.
