# Phase 25 Retired Wrapper Pre-Delete Readiness

Date: 2026-06-29

Scope: prove the remaining retired compatibility wrappers are ready for
explicit one-file-at-a-time deletion, without deleting any file in this phase.

## Current State

`investment_system/pipelines/` currently contains only:

- `investment_system/pipelines/README.md`
- `investment_system/pipelines/evidence_overrides.py`
- `investment_system/pipelines/run_research.py`

The two Python files are registered retired compatibility surfaces:

| Path | Current role | Target implementation | Required next action |
|---|---|---|---|
| `investment_system/pipelines/evidence_overrides.py` | thin compatibility wrapper | `investment_system.core.evidence_merge` | first deletion candidate after explicit path confirmation |
| `investment_system/pipelines/run_research.py` | thin compatibility wrapper | `investment_system.core.legacy_broad_cli` | second deletion candidate after first deletion validates |

## Readiness Evidence

Command:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py retired-surfaces --project tech_ai_semiconductor --deletion-stage no-delete --json
```

Result summary:

| Check | Result |
|---|---|
| Severity summary | `HIGH=0`, `LOW=0`, `INFO=9` |
| `evidence_overrides.py` | present, thin wrapper, SHA256 `420F144E11B49330DC80758EA44926AB46872898E04B9A1514ADBBB502512945` |
| `run_research.py` | present, thin wrapper, SHA256 `632A1FD848CC4D5E98C917BB0D2925ABE3086604EDFE2BF42D99B7A02FA8DF38` |
| Active Python imports | none found for the retired modules |
| Active skill guidance | no retired wrapper file paths under `.codex/skills/**/*.md` |
| Pipeline directory boundary | only README plus registered retired compatibility surfaces |
| Deletion stage | `no-delete` matched: both retired wrappers present |

Formal output boundary check:

| Check | Result |
|---|---|
| formal file count | 3 |
| forbidden total/log file count | 0 |

## Deletion Sequence To Use After Confirmation

Do not treat this file as authorization. Deletion still requires the user to
explicitly confirm the exact path.

1. Delete only:

```powershell
Remove-Item "C:\Projects\03_Investment\investment_system\pipelines\evidence_overrides.py"
```

Then validate:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py retired-surfaces --project tech_ai_semiconductor --deletion-stage after-evidence-overrides
```

2. Only after the first deletion validates, delete:

```powershell
Remove-Item "C:\Projects\03_Investment\investment_system\pipelines\run_research.py"
```

Then validate:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py retired-surfaces --project tech_ai_semiconductor --deletion-stage after-run-research
```

## Decision

No deletion was performed in Phase 25.

The remaining blocker is not technical readiness. The only remaining required
input is explicit user confirmation for the exact first path:

`C:\Projects\03_Investment\investment_system\pipelines\evidence_overrides.py`
