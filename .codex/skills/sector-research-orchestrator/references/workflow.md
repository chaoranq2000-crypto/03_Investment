# Workflow

## Standard Run

0. Scope the task.
   - Read `A股科技前两主线调研文件包/02_Codex调研说明手册/Codex调研说明手册.md`.
   - Read the relevant rows in `A股科技前两主线调研文件包/01_调研板块细分方向列表/A股科技前两主线_板块细分方向母表.csv`.
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
   - Evidence output: `investment_system/research/evidence/<theme_slug>.yaml`.
   - Acceptance: material claims have source rows with local cache paths or webpage URLs, or remain in the missing-data log.

4. Forecast step: call `forecast-normalizer`.
   - Purpose: 2026E/2027E revenue/profit, PE, PEG, forecast institution count, forecast-change notes.
   - Evidence output: update `company_overrides` in the evidence YAML.
   - Acceptance: public-source, user-provided, single-broker, and judgment values are clearly labeled. Do not claim Wind/iFind consensus unless the user supplies the source data.

5. Writing step: call `research-writer`.
   - Purpose: generate card, company table, comparison table, source index, missing/conflict/research logs.
   - Command:

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\pipelines\run_research.py --sub-theme "高速光模块" --skip-guosen
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\pipelines\cleanup_outputs.py
```

6. Audit step: call `quality-auditor`.
   - Purpose: check missing fields, semantic CSV shifts, duplicate source IDs, stale dates, no-source assertions, conflicts, and report depth.
   - Command:

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\pipelines\validate_outputs.py --sub-theme "高速光模块"
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\pipelines\validate_outputs.py --sub-theme "高速光模块" --grade research
```

7. Repair loop.
   - If market data fails, return to `market-data-router`.
   - If financial values are inconsistent, return to `financial-data-router`.
   - If assertions lack sources, return to `evidence-miner`.
   - If forward valuations are unclear, return to `forecast-normalizer`.
   - If output schema breaks, return to `research-writer`.
   - If validation misses a class of error, update `quality-auditor` and `validate_outputs.py`.

## Output Files

- `科技主线调研输出/00_总表/科技细分方向横向比较表.csv`
- `科技主线调研输出/00_总表/代表公司财务估值总表.csv`
- `科技主线调研输出/00_总表/数据来源索引.csv`
- `科技主线调研输出/01_AI算力硬件/NN_细分方向.md`
- `科技主线调研输出/02_半导体国产替代/NN_细分方向.md`
- `科技主线调研输出/99_日志/缺失数据清单.md`
- `科技主线调研输出/99_日志/冲突数据清单.md`
- `科技主线调研输出/99_日志/调研日志.md`

## Current Known Caveat

`高速光模块` now has a curated evidence file:

```text
investment_system/research/evidence/high_speed_optical_modules.yaml
```

Do not edit final CSV/Markdown as the source of truth. Update the evidence file or the pipeline, then rerun the standard commands.

P1 directions may have only debug-grade evidence at first. Do not treat a pipeline-grade pass as final. Research-grade requires independently readable prose, company-level depth, and verifiable sources.
