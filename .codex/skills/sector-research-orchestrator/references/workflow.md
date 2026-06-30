# Workflow

This file is an operator guide, not the authoritative project workflow policy.

For `tech_ai_semiconductor`, the source of truth for stage order, CLI routing, default modes, write boundaries, manual-confirmation requirements, publish scope, and warning-only exit handling is:

- `investment_system/research/projects/tech_ai_semiconductor/workflow_stages.yaml`

## Operator Use

Start with `workflow_stages.yaml`, then use the orchestrator stage runner:

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\sector-research-orchestrator\scripts\cli.py run-stage --project tech_ai_semiconductor --sector-id <canonical_sector_id> --stage <stage_name>
```

Use the scope-check shortcut before a new phase:

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\sector-research-orchestrator\scripts\cli.py scope-check --project tech_ai_semiconductor
```

For stage-specific inputs, read the owning skill's `SKILL.md` and contract reference:

- `market-data-router`: market K-line, quote, turnover, relative-strength, and fund-flow inputs.
- `financial-data-router`: financial statements, indicators, equity, dividends, and valuation inputs.
- `evidence-miner`: raw source manifests, draft evidence skeletons, curated evidence validation, and evidence registration.
- `forecast-normalizer`: broker/user/public forecast normalization and forward valuation labels.
- `research-writer`: candidate-only output generation from structured inputs.
- `quality-auditor`: evidence, candidate, publish, post-publish, and output validation gates.

If validation fails, repair the failing lower skill or source layer instead of editing final Markdown or CSV outputs by hand.

## Stage Defaults

Stage defaults are intentionally not copied here. Read `workflow_stages.yaml` for each stage's current default mode, allowed writes, forbidden writes, manual-confirmation requirement, and warning-only handling.

## Output Files

Output paths are resolved dynamically from project config via `python -m investment_system.core.project_loader --project <id> --dry-run-paths`. Do not hard-code fixed paths in skill logic.

Typical output structure (resolved from project config):
- `<output_root>/00_总表/代表公司财务估值总表.csv`
- `<output_root>/00_总表/科技细分方向横向比较表.csv`
- `<output_root>/00_总表/数据来源索引.csv`
- `<output_root>/<group_order>_<group_name>/<priority>_<sector_name>.md`
- `<output_root>/99_日志/缺失数据清单.md`
- `<output_root>/99_日志/冲突数据清单.md`
- `<output_root>/99_日志/调研日志.md`

Formal publish shape and formal-output write permission are controlled by `workflow_stages.yaml`. Do not infer write permission from the typical output list above.

## Current Known Caveat

Project-aware evidence files are stored under `investment_system/research/evidence/` with canonical `sector_id` naming.

Do not edit final CSV/Markdown as the source of truth. Update the evidence file or the pipeline, then rerun the standard commands.

P1 directions may have only debug-grade evidence at first. Do not treat a pipeline-grade pass as final. Research-grade requires independently readable prose, company-level depth, and verifiable sources.
