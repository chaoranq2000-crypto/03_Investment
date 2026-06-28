# Workflow

This file is the current operational workflow reference.

## Standard Run

0. Scope the task.
   - Read `investment_system/research/projects/<project_id>/project.yaml`.
   - Read `investment_system/research/projects/<project_id>/sector_universe.yaml` for canonical sector definitions.
   - Read `investment_system/research/projects/<project_id>/stock_universe.yaml` for project-aware stock pools.
   - Inspect current outputs before writing.
   - For data-source health, run `investment_system/scripts/check_data_sources.py`; use `market-data-router tushare-ping` or `financial-data-router tushare-ping` only when Tushare connectivity matters.
   - Prefer the skill CLI scope check:

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\sector-research-orchestrator\scripts\cli.py scope-check --project tech_ai_semiconductor --sector-id <canonical_sector_id>
```

1. Market data step: call `market-data-router`.
   - Purpose: K-line, latest price, 1/3/6 month return, turnover, index relative strength, realtime/fund-flow diagnostics.
   - Script boundary: `investment_system/scripts/research_client.py`.
   - Raw output: `investment_system/data/raw/<source>/<dataset>/<date>/`.
   - Acceptance: all representative companies have daily rows or explicit failure records.

2. Financial data step: call `financial-data-router`.
   - Purpose: revenue, net profit, gross margin, net margin, EPS, total shares, PE TTM, PS TTM.
   - Script boundary: `investment_system/scripts/research_client.py`, `market-data-router` / `financial-data-router` Tushare CLI diagnostics, and project-aware output writers/validators.
   - Raw output: `investment_system/data/raw/baostock/profit/<date>/`.
   - Acceptance: financial units are normalized and derived valuation fields are filled or logged as missing.

3. Evidence mining step: call `evidence-miner`.
   - Purpose: business exposure, customer/order evidence, capacity, product stage, policy catalyst, risk evidence.
   - If configured interfaces cannot fill a required field, run web evidence mining before accepting the gap.
   - Source priority: annual/interim/quarterly reports, announcements, investor-relations records, exchange Q&A, policy documents, broker reports, then media only as weak context.
   - Raw source handoff: first build a source manifest under `investment_system/data/raw/official_evidence/`.
   - Draft evidence output: then build a YAML skeleton under `investment_system/research/projects/<project_id>/audits/evidence_drafts/`.
   - Active evidence output: only after manual excerpt/claim curation should a file be promoted into `investment_system/research/evidence/<sector_id>.yaml`.
   - For bundled Tushare JSON caches, first split by dataset before drafting:

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\evidence-miner\scripts\cli.py split-tushare-cache --project tech_ai_semiconductor --sector-id <canonical_sector_id> --cache-path investment_system/data/raw/tushare/<cache>.json
```

   - Add `--write-split --write-manifest` only when writing dataset-level raw cache files and a source manifest is intended.
   - Source-manifest collection command:

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\evidence-miner\scripts\cli.py collect --project tech_ai_semiconductor --sector-id <canonical_sector_id> --local-dir investment_system/data/raw/cninfo/<source_set>/<date> --extensions .pdf
```

   - Add `--write-manifest` only when writing a raw source manifest under `investment_system/data/raw/official_evidence/` is intended.
   - Draft skeleton command:

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\evidence-miner\scripts\cli.py draft --project tech_ai_semiconductor --sector-id <canonical_sector_id> --source-manifest investment_system/data/raw/official_evidence/<project_id>/<sector_id>/<date>/source_manifest_<sector_id>_<source_set>_<date>.json
```

   - Add `--write-draft` only when writing a draft YAML skeleton under the project audit directory is intended.
   - Draft skeletons use `status: draft_source_skeleton` and `DRAFT_PLACEHOLDER` claims; they must not be registered as active evidence until the placeholder excerpt and claim fields are manually curated.
   - Curated evidence can be checked directly before registration:

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\evidence-miner\scripts\cli.py validate-curated --evidence-path investment_system/research/evidence/<file>.yaml
```

   - Registration command:

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\evidence-miner\scripts\cli.py register --project tech_ai_semiconductor --sector-id <canonical_sector_id> --path investment_system/research/evidence/<file>.yaml
```

   - Use `register-apply` only when the intended writes to `run_manifest.yaml` and `sector_universe.yaml` are in scope.

   - Acceptance: material claims have active evidence rows with local cache paths or webpage URLs, or remain in missing evidence / risk / conflict notes.

4. Forecast step: call `forecast-normalizer`.
   - Purpose: 2026E/2027E revenue/profit, PE, PEG, forecast institution count, forecast-change notes.
   - Evidence output: update `company_overrides` in the evidence YAML.
   - Acceptance: public-source, user-provided, single-broker, and judgment values are clearly labeled. Do not claim Wind/iFind consensus unless the user supplies the source data.

5. Candidate step: call `research-writer` through its skill CLI.
   - Purpose: generate candidate-only review artifacts under the project audit directory.
   - It must not generate gated formal files, release manifests, formal score tables, or formal output-root files.
   - It must not turn missing evidence into deterministic claims.
   - It must preserve `NOT_RATED` and `NOT_INVESTMENT_ADVICE` unless a separate explicit scoring/investment process is in scope.
   - Candidate-only command:

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\research-writer\scripts\cli.py generate-candidate --write-candidate --project tech_ai_semiconductor --sector-id <canonical_sector_id>
```

6. Candidate Gate and Publish Gate: call `quality-auditor`.
   - `candidate_gate` checks content quality, source/evidence traceability, missing evidence retention, conflict/counter-evidence, no draft placeholders, and no investment advice.
   - `publish_gate` is dry-run only. It checks target path, no-overwrite, source hash, excluded outputs, and `sector_card_only`.

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\quality-auditor\scripts\cli.py candidate-gate --project tech_ai_semiconductor --sector-id <canonical_sector_id>
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\sector-research-orchestrator\scripts\cli.py publish-gate --project tech_ai_semiconductor --sector-id <canonical_sector_id> --publish-scope sector_card_only
```

7. Formal sector-card-only publish, only after explicit user confirmation.
   - This is the only simplified-flow stage that may write the formal output root.
   - It must be `sector_card_only`, use `--no-overwrite`, and write exactly one sector card plus the audit publish log.
   - Do not publish total tables, formal source indexes, score tables, comparison tables, release manifests, or investment advice.

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\sector-research-orchestrator\scripts\cli.py publish-sector-card-only --project tech_ai_semiconductor --sector-id <canonical_sector_id> --confirm-publish
```

8. Post-publish Check: call `quality-auditor`.
   - Verifies source hash equals target hash, formal card count, forbidden artifact absence, publish log, `validate_outputs`, and readiness.

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\quality-auditor\scripts\cli.py post-publish-check --project tech_ai_semiconductor --sector-id <canonical_sector_id>
```

9. Legacy broad command, only when the user explicitly asks for broad generation:

```powershell
# Project-aware single sector:
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\pipelines\run_research.py --project tech_ai_semiconductor --sector-id <canonical_sector_id> --skip-guosen
# After generation, validate the structural contract:
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\quality-auditor\scripts\cli.py validate-outputs --project tech_ai_semiconductor
```

10. Repair loop.
   - If market data fails, return to `market-data-router`.
   - If financial values are inconsistent, return to `financial-data-router`.
   - If assertions lack sources, return to `evidence-miner`.
   - If forward valuations are unclear, return to `forecast-normalizer`.
   - If output schema breaks, return to `research-writer`.
   - If validation misses a class of error, update `quality-auditor` and the relevant gate script.

## Stage Defaults

- `scope_check`: read-only except audit summaries.
- `evidence_collect`: preview by default; `--write-manifest` writes raw source manifests only.
- `evidence_draft`: preview by default; `--write-draft` writes draft skeletons under audits only.
- `evidence_register`: dry-run by default; `--apply-registration` updates `run_manifest.yaml` and `sector_universe.yaml`.
- `evidence_gate`: audit-only.
- `generate_candidate`: writes candidate artifacts under audits only.
- `candidate_gate`: audit-only, with optional metadata gate-status update for passing candidates.
- `publish_gate`: dry-run manifest/readiness only.
- `publish_sector_card_only`: formal write, manual confirmation required.
- `post_publish_check`: audit-only.

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

For the current simplified formal flow, the only supported formal publish shape is sector-card-only. The stage policy lives at:

- `investment_system/research/projects/tech_ai_semiconductor/workflow_stages.yaml`

Do not write the formal output root during scope checks, evidence gates, candidate generation, candidate gates, or publish gates. The only simplified-flow formal write is `publish_sector_card_only` after explicit user confirmation.

## Current Known Caveat

Project-aware evidence files are stored under `investment_system/research/evidence/` with canonical `sector_id` naming.

Do not edit final CSV/Markdown as the source of truth. Update the evidence file or the pipeline, then rerun the standard commands.

P1 directions may have only debug-grade evidence at first. Do not treat a pipeline-grade pass as final. Research-grade requires independently readable prose, company-level depth, and verifiable sources.
