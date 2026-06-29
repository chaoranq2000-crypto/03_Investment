# Tushare-First Data Skill Refactor Summary

Created: 2026-06-29
Project: `tech_ai_semiconductor`
Scope: project-local Codex skills, data-fetch workflow, raw cache, source-manifest handoff
Status: first implementation pass complete

This is an engineering summary. It is not a formal research output, not investment advice, and not a sector card.

## 1. Executive Summary

The data-fetching workflow has been refactored from a BaoStock/AKShare/Tencent-oriented surface into a Tushare-first, skill-owned collection layer.

The main refactor is complete at the skill and interface-contract level:

- `market-data-router`, `financial-data-router`, `evidence-miner`, and `forecast-normalizer` now expose Tushare-first commands.
- Shared Tushare request logic lives under `.codex/skills/market-data-router/src/tushare_data_router/`, not under `investment_system/core/`.
- Tushare rows can be saved as raw-cache envelopes and converted into source-manifest records.
- `quality-auditor` now has a Tushare raw-cache audit command for schema and secret-leakage checks.
- `a-stock-data` is integrated as a reference for public-web fallback patterns, not as the primary architecture.

The refactor is intentionally Tushare-first, not Tushare-only. Tushare is the main structured data source; Tencent, CNINFO, Eastmoney, Tonghuashun, Sina, BaoStock, and AKShare remain fallback or complementary sources when they are stronger for a specific need.

## 2. Why This Refactor Was Needed

Before this work, the project data skills were still relatively coarse:

- market and financial commands were mainly wrappers around legacy `ResearchClient` routes;
- source priority still described BaoStock/AKShare as primary for daily K-line and financial data;
- the 8-12 second AKShare-style wait policy was too broad for Tushare proxy/API usage;
- Tushare usage existed, but was not broad enough across market, financial, evidence, forecast, macro, fund/ETF, convertible-bond, and cross-asset datasets;
- raw data and evidence promotion needed a clearer boundary so API rows would not turn directly into unsupported research claims.

The desired direction is:

```text
Tushare API rows
  -> raw cache envelope
  -> source manifest
  -> evidence draft
  -> manually curated active evidence
  -> candidate/formal outputs only after gates pass
```

## 3. Architecture Decisions

### Skill-Owned Business Logic

Broad endpoint logic now belongs in skill modules:

```text
.codex/skills/market-data-router/src/tushare_data_router/
  __init__.py
  commands.py
  datasets.py
  rate_limit.py
  raw_cache.py
```

This keeps `investment_system/core/` focused on shared project semantics and small facades such as project loading and Tushare connection setup.

### Shared Router, Multiple Skill Surfaces

The same Tushare router is delegated from multiple skills:

- `market-data-router`: market, valuation, trading behavior, theme heat, macro/cross-asset context.
- `financial-data-router`: statements, indicators, holders, dividends, repurchase, company profile.
- `evidence-miner`: announcement/report/survey/Q&A/news indexes.
- `forecast-normalizer`: broker forecast rows and report metadata.

This avoids copying request/caching code across skills.

### Dry-Run First

All new data-fetch commands are dry-run by default.

- `--fetch` performs live calls.
- `--write-cache` writes raw-cache envelopes.
- `--write-manifest` writes source-manifest records.

This matches the project rule that data collection, evidence curation, and formal output generation must remain separated.

## 4. New Command Surface

### Market Data

Examples:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\market-data-router\scripts\cli.py tushare-fetch --group market
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\market-data-router\scripts\cli.py daily-kline --code 000001.SZ
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\market-data-router\scripts\cli.py daily-basic --project tech_ai_semiconductor --sector-id high_speed_copper_connector
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\market-data-router\scripts\cli.py moneyflow --code 000001.SZ
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\market-data-router\scripts\cli.py dragon-tiger --trade-date 20260626
```

Current Tushare-first market aliases include:

- `daily-kline`
- `daily-basic`
- `moneyflow`
- `dragon-tiger`
- `margin`
- `limit-list`
- `sector-theme`
- `index-daily`
- `fund-etf-daily`
- `convertible-bond-daily`

Legacy compatibility remains available through:

- `legacy-daily-kline`
- `legacy-index-daily`
- existing Tencent/ResearchClient compatibility commands

### Financial Data

Examples:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\financial-data-router\scripts\cli.py tushare-fetch --group financial
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\financial-data-router\scripts\cli.py income --code 000001.SZ --period 20250331
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\financial-data-router\scripts\cli.py fina-indicator --project tech_ai_semiconductor --sector-id high_speed_copper_connector
```

Current Tushare-first financial aliases include:

- `income`
- `balancesheet`
- `cashflow`
- `fina-indicator`
- `main-business`
- `holders`
- `share-float`
- `dividend`
- `repurchase`
- `valuation-snapshot`

The old `profit` command is retained as BaoStock compatibility.

### Evidence Indexes

Examples:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\evidence-miner\scripts\cli.py tushare-fetch --group evidence
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\evidence-miner\scripts\cli.py research-report-index --code 000001.SZ
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\evidence-miner\scripts\cli.py tushare-source-manifest --project tech_ai_semiconductor --sector-id high_speed_copper_connector --cache-path investment_system\data\raw\tushare\daily\2026-06-29\000001.SZ.json
```

Current evidence aliases include:

- `announcements-index`
- `research-report-index`
- `survey-index`
- `irm-qa-index`
- `tushare-source-manifest`

These commands produce source rows or source-manifest views. They do not automatically create active evidence.

### Forecast Normalization

Examples:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\forecast-normalizer\scripts\cli.py report-rc --code 000001.SZ
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\forecast-normalizer\scripts\cli.py normalize-forecast-fields --project tech_ai_semiconductor --sector-id high_speed_copper_connector
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\forecast-normalizer\scripts\cli.py audit-forecast-source-count --cache-path <json>
```

Current forecast commands include:

- `tushare-fetch`
- `report-rc`
- `research-report-index`
- `normalize-forecast-fields`
- `audit-forecast-source-count`

Forecast rows are labeled as source rows, not automatically as consensus.

## 5. Dataset Coverage Added

The dataset registry is declarative and lives in:

```text
.codex/skills/market-data-router/src/tushare_data_router/datasets.py
```

### Market and Trading

Representative datasets:

- `stock_basic`
- `trade_cal`
- `daily`
- `daily_basic`
- `adj_factor`
- `moneyflow`
- `top_list`
- `limit_list_d`
- `margin_detail`
- `index_daily`
- `fund_daily`
- `cb_daily`
- `cb_basic`
- `ths_hot`
- `stk_mins`

### Financial and Governance

Representative datasets:

- `income`
- `balancesheet`
- `cashflow`
- `fina_indicator`
- `fina_mainbz`
- `stock_company`
- `stk_managers`
- `stk_rewards`
- `top10_holders`
- `stk_holdernumber`
- `share_float`
- `pledge_detail`
- `dividend`
- `repurchase`

### Evidence Discovery

Representative datasets:

- `anns_d`
- `research_report`
- `stk_surv`
- `irm_qa_sz`
- `irm_qa_sh`
- `news`

Some of these may require separate Tushare permissions. Permission failure is expected to be reported as a fetch error, not silently replaced by another source.

### Forecast

Representative datasets:

- `report_rc`
- `research_report`

### Macro and Cross-Asset Context

Representative datasets:

- `cn_gdp`
- `cn_cpi`
- `cn_ppi`
- `cn_pmi`
- `shibor`
- `hk_basic`
- `hk_daily`
- `us_basic`
- `us_daily`
- `fut_basic`
- `fut_daily`
- `opt_basic`
- `opt_daily`

These are context datasets and should not be promoted into sector evidence without a clear research purpose.

## 6. Data Format Alignment

### Raw Cache Envelope

Fetched Tushare rows are saved using a stable envelope:

```json
{
  "schema_version": "tushare_raw_cache.v1",
  "source": "tushare",
  "group": "market",
  "dataset": "daily",
  "api_name": "daily",
  "project_id": "tech_ai_semiconductor",
  "sector_id": "high_speed_copper_connector",
  "stock": {
    "stock_code": "000001",
    "market": "SZ",
    "ts_code": "000001.SZ",
    "stock_name": ""
  },
  "request": {
    "params": {},
    "fields": "",
    "row_limit": 1
  },
  "fetch_status": "ok",
  "row_count": 1,
  "rows": []
}
```

Important properties:

- the Tushare token and private bridge configuration are omitted;
- request parameters and fields are preserved;
- project and sector context are preserved when provided;
- rows remain raw data and are not treated as curated research evidence.

### Source Manifest Record

Raw envelopes can be converted into source-manifest records with:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\evidence-miner\scripts\cli.py tushare-source-manifest --project tech_ai_semiconductor --sector-id high_speed_copper_connector --cache-path <json>
```

The generated source record includes:

- `source_id`
- `project_id`
- `sector_id`
- `source_type`
- `evidence_level`
- `company_code`
- `company_name`
- `title`
- `publisher`
- `source_date`
- `local_path`
- `file_sha256`
- `access_method`
- `parser`
- `parser_status`

This aligns the data layer with the evidence/source interface.

## 7. Evidence Boundary

The refactor deliberately does not allow raw Tushare rows to become active evidence automatically.

Allowed:

```text
Tushare row -> raw cache -> source manifest -> evidence draft
```

Blocked without manual curation:

```text
Tushare row -> active evidence
Tushare row -> final report claim
Tushare row -> investment conclusion
```

This matters because database rows can support financial, market, and source-index fields, but cannot by themselves prove:

- product stage;
- customer binding;
- order certainty;
- capacity progress;
- supply-chain exclusivity;
- investment conclusion or rating.

Those still require annual reports, announcements, IR records, exchange Q&A, policy files, broker report text, or manually curated source excerpts.

## 8. a-stock-data Integration Role

The installed `a-stock-data` skill is useful, but it is not adopted as the main architecture.

What is reused or referenced:

- source-specific route thinking;
- ticker normalization patterns;
- Tencent direct quote and valuation fallback ideas;
- Eastmoney session reuse and anti-ban rate-limit policy;
- CNINFO, Tonghuashun, Sina, Eastmoney, iwencai endpoint patterns;
- the principle that public-web data should be used for unique capabilities, not as a high-frequency default.

What is not adopted:

- a single large all-in-one skill as the main workflow;
- direct public-web scraping as the primary structured data layer;
- bypassing project-aware `project_id`, `sector_id`, raw cache, source manifest, and evidence gates.

## 9. Rate-Limit Policy

The previous broad 8-12 second wait policy is now source-specific:

| Source | Policy |
|---|---|
| Tushare proxy/API | serial by default, 0.7s + small jitter; configurable by CLI/env |
| Eastmoney public web | serial, session reuse, at least 1s + jitter; 1.5-2s for batches |
| AKShare public web | small-batch fallback, 8-12s + jitter for Eastmoney-like endpoints |
| Tencent direct | small batches, modest loop wait |
| BaoStock | one session per batch, avoid repeated login/logout |
| CNINFO/official web | targeted low-concurrency fetches with local cache |

The Tushare router exposes:

- `--interval`
- `--jitter`
- `TUSHARE_REQUEST_INTERVAL_SECONDS`
- `TUSHARE_REQUEST_JITTER_SECONDS`

## 10. Validation Performed

Validation commands used during implementation included:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe -m py_compile <touched python files>
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\market-data-router\scripts\cli.py --help
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\financial-data-router\scripts\cli.py --help
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\evidence-miner\scripts\cli.py --help
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\forecast-normalizer\scripts\cli.py --help
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py tushare-raw-cache --path investment_system\data\raw\tushare
```

Current raw-cache audit result:

```text
files_checked: 7
error_count: 0
warn_count: 0
```

Additional validation performed:

- dry-run request planning for market, financial, evidence, and forecast groups;
- project/sector stock resolution through `stock_universe.yaml`;
- live Tushare fetch for a minimal `daily` request after local private Tushare configuration was updated;
- source-manifest view generation from the new raw-cache envelope;
- `git diff --check` on the touched refactor surface.

Known non-blocking project warnings remain from existing project state:

- retired compatibility wrapper notices;
- legacy evidence fields retained for compatibility;
- unused source IDs in older evidence YAML;
- some project coverage warnings;
- missing optional schema files referenced by older audit surfaces.

These were not introduced by the Tushare-first refactor.

## 11. Files Added

Core new implementation:

```text
.codex/skills/market-data-router/src/tushare_data_router/__init__.py
.codex/skills/market-data-router/src/tushare_data_router/commands.py
.codex/skills/market-data-router/src/tushare_data_router/datasets.py
.codex/skills/market-data-router/src/tushare_data_router/rate_limit.py
.codex/skills/market-data-router/src/tushare_data_router/raw_cache.py
.codex/skills/forecast-normalizer/src/forecast_normalizer/forecast_tools.py
.codex/skills/quality-auditor/src/quality_auditor/tushare_raw_cache.py
```

Planning and validation artifacts:

```text
investment_system/research/projects/tech_ai_semiconductor/tushare_first_data_skill_refactor_plan.md
investment_system/research/projects/tech_ai_semiconductor/audits/tushare_first_data_skill_refactor_summary_20260629.md
investment_system/data/raw/tushare/daily/2026-06-29/000001.SZ.json
investment_system/data/raw/tushare/source_manifests/tech_ai_semiconductor/high_speed_copper_connector/2026-06-29/source_manifest_tushare_tech_ai_semiconductor_high_speed_copper_connector_2026-06-29.json
```

## 12. Files Modified

Skill command and documentation surfaces:

```text
.codex/skills/market-data-router/SKILL.md
.codex/skills/market-data-router/src/market_data_router/commands.py
.codex/skills/financial-data-router/SKILL.md
.codex/skills/financial-data-router/src/financial_data_router/commands.py
.codex/skills/evidence-miner/SKILL.md
.codex/skills/evidence-miner/src/evidence_miner/commands.py
.codex/skills/evidence-miner/src/evidence_miner/tushare_cache_split.py
.codex/skills/forecast-normalizer/SKILL.md
.codex/skills/forecast-normalizer/src/forecast_normalizer/commands.py
.codex/skills/quality-auditor/SKILL.md
.codex/skills/quality-auditor/src/quality_auditor/commands.py
.codex/skills/sector-research-orchestrator/references/data_sources.md
```

Configuration:

```text
investment_system/config/data_sources.example.toml
investment_system/config/.env.local
```

Note: `.env.local` is private local configuration and should not be committed or printed. It was updated so the default Tushare route uses the working bridge URL and token.

## 13. Current Limitations

This refactor completes the first implementation pass, but not every possible data-source integration is finished.

Remaining limits:

- not every Tushare endpoint has been live-tested;
- announcement, research-report, and interactive-Q&A datasets may still depend on token permissions;
- public-web fallback adapters from `a-stock-data` are not all ported into project-local scripts;
- forecast normalization has preview/source-count tooling but not a full formal forecast table writer;
- raw API rows still require curation before active evidence registration;
- formal output generation is intentionally out of scope for this refactor.

## 14. Recommended Next Steps

### Step 1: Small-Batch Sector Cache

Run focused cache writes for one sector:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\market-data-router\scripts\cli.py daily-basic --project tech_ai_semiconductor --sector-id high_speed_copper_connector --limit 5 --fetch --write-cache --write-manifest
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\financial-data-router\scripts\cli.py income --project tech_ai_semiconductor --sector-id high_speed_copper_connector --limit 5 --period 20250331 --fetch --write-cache --write-manifest
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\financial-data-router\scripts\cli.py fina-indicator --project tech_ai_semiconductor --sector-id high_speed_copper_connector --limit 5 --period 20250331 --fetch --write-cache --write-manifest
```

### Step 2: Source Manifest to Evidence Draft

Use source manifests as input for draft evidence, then manually curate excerpts and claims.

Do not register raw cache rows directly as active evidence.

### Step 3: Permission Matrix

Build a small Tushare permission matrix for:

- `anns_d`
- `research_report`
- `stk_surv`
- `irm_qa_sz`
- `irm_qa_sh`
- `report_rc`

Mark each as:

- available;
- empty due to date/params;
- permission denied;
- fallback needed.

### Step 4: Public-Web Fallback Adapters

Only after a Tushare permission or coverage gap is confirmed, port targeted `a-stock-data` patterns into project-local adapters.

Candidate fallback areas:

- CNINFO announcement full-text search/download;
- Eastmoney report metadata/PDF;
- Tencent quote sanity checks;
- Tonghuashun heat/reason tags;
- Eastmoney theme/flow/ranking endpoints.

### Step 5: Quality Gates

For every new batch:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py tushare-raw-cache --path investment_system\data\raw\tushare
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py evidence-schema --project tech_ai_semiconductor
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py pipeline-readiness --project tech_ai_semiconductor
```

## 15. Completion Assessment

Current assessment:

- Skill refactor: complete for the first Tushare-first implementation pass.
- Tushare router: implemented and shared across data skills.
- Data format alignment: complete at raw-cache envelope level.
- Evidence interface alignment: complete at source-manifest handoff level.
- Evidence curation: intentionally manual and not automated.
- Full endpoint coverage: expanded substantially but not exhaustively live-validated.
- Public-web fallback integration: documented and partially designed, not fully ported.

Practical conclusion:

The project now has a workable Tushare-first data ingestion spine. The next stage should be controlled sector-level cache population and evidence-draft promotion, not more broad architectural reshuffling.
