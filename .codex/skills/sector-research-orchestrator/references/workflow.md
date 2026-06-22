# Workflow

## Standard Run

0. Scope the task.
   - Read `investment_system/research/projects/<project_id>/project.yaml`.
   - Read `investment_system/research/projects/<project_id>/sector_universe.yaml` for canonical sector definitions.
   - Read `investment_system/research/projects/<project_id>/stock_universe.yaml` for project-aware stock pools.
   - Inspect current outputs before writing.
   - For data-source health, run `investment_system/scripts/check_data_sources.py`; use `investment_system/pipelines/tushare_client.py --ping` only when Tushare connectivity matters.

1. Market data step: call `market-data-router`.
   - Purpose: K-line, latest price, 1/3/6 month return, turnover, index relative strength, realtime/fund-flow diagnostics.
   - Script boundary: `investment_system/scripts/research_client.py`.
   - Raw output: `investment_system/data/raw/<source>/<dataset>/<date>/`.
   - Acceptance: all representative companies have daily rows or explicit failure records.

2. Financial data step: call `financial-data-router`.
   - Purpose: revenue, net profit, gross margin, net margin, EPS, total shares, PE TTM, PS TTM.
   - Script boundary: `investment_system/scripts/research_client.py`, `investment_system/pipelines/tushare_client.py`, and `investment_system/pipelines/cleanup_outputs.py`.
   - Raw output: `investment_system/data/raw/baostock/profit/<date>/`.
   - Acceptance: financial units are normalized and derived valuation fields are filled or logged as missing.

3. Evidence mining step: call `evidence-miner`.
   - Purpose: business exposure, customer/order evidence, capacity, product stage, policy catalyst, risk evidence.
   - If configured interfaces cannot fill a required field, run web evidence mining before accepting the gap.
   - Evidence output: `investment_system/research/evidence/<sector_id>.yaml` (project-aware path).
   - Acceptance: material claims have source rows with local cache paths or webpage URLs, or remain in the missing-data log.

4. Forecast step: call `forecast-normalizer`.
   - Purpose: 2026E/2027E revenue/profit, PE, PEG, forecast institution count, forecast-change notes.
   - Evidence output: update `company_overrides` in the evidence YAML.
   - Acceptance: public-source, user-provided, single-broker, and judgment values are clearly labeled. Do not claim Wind/iFind consensus unless the user supplies the source data.

5. Writing step: call `research-writer`.
   - Purpose: generate card, company table, comparison table, source index, missing/conflict/research logs.
   - Command:

```powershell
# Project-aware single sector:
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\pipelines\run_research.py --project tech_ai_semiconductor --sector-id <canonical_sector_id> --skip-guosen
# After generation:
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\pipelines\cleanup_outputs.py
```

6. Audit step: call `quality-auditor`.
   - Purpose: check missing fields, semantic CSV shifts, duplicate source IDs, stale dates, no-source assertions, conflicts, and report depth.
   - Command:

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\pipelines\validate_outputs.py --project tech_ai_semiconductor --sector-id <sector_id>
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\pipelines\validate_outputs.py --project tech_ai_semiconductor --sector-id <sector_id> --grade research
```

7. Repair loop.
   - If market data fails, return to `market-data-router`.
   - If financial values are inconsistent, return to `financial-data-router`.
   - If assertions lack sources, return to `evidence-miner`.
   - If forward valuations are unclear, return to `forecast-normalizer`.
   - If output schema breaks, return to `research-writer`.
   - If validation misses a class of error, update `quality-auditor` and `validate_outputs.py`.

## Output Files

Output paths are resolved dynamically from project config via `load_project --project <id> --dry-run-paths`. Do not hard-code fixed paths in skill logic.

Typical output structure (resolved from project config):
- `<output_root>/00_总表/代表公司财务估值总表.csv`
- `<output_root>/00_总表/科技细分方向横向比较表.csv`
- `<output_root>/00_总表/数据来源索引.csv`
- `<output_root>/<group_order>_<group_name>/<priority>_<sector_name>.md`
- `<output_root>/99_日志/缺失数据清单.md`
- `<output_root>/99_日志/冲突数据清单.md`
- `<output_root>/99_日志/调研日志.md`

## Current Known Caveat

Project-aware evidence files are stored under `investment_system/research/evidence/` with canonical `sector_id` naming.

Do not edit final CSV/Markdown as the source of truth. Update the evidence file or the pipeline, then rerun the standard commands.

P1 directions may have only debug-grade evidence at first. Do not treat a pipeline-grade pass as final. Research-grade requires independently readable prose, company-level depth, and verifiable sources.
