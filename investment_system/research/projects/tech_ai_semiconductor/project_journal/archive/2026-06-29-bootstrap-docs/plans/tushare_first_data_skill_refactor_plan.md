# Tushare-First Data Skill Refactor Plan

Created: 2026-06-29
Scope: `tech_ai_semiconductor` project-aware data collection workflow and project-local Codex skills
Status: implementation in progress, safe to update during implementation

This file is an engineering plan. It is not a formal research output, not investment advice, and not a generated sector artifact.

## 0. Implementation Status

Updated: 2026-06-29

- Draft rollback completed: the earlier experimental `tushare_data_router/__init__.py` and `commands.py` files were removed before the formal implementation was added.
- Phase A/B implemented: a skill-owned shared Tushare router now lives under `.codex/skills/market-data-router/src/tushare_data_router/`.
- Phase C implemented for command surfaces: market, financial, evidence, and forecast skills expose `tushare-fetch` plus dataset aliases.
- Phase D documented: `a-stock-data` is used as the public-web fallback reference for endpoint patterns, ticker normalization, session reuse, and source-specific rate limits.
- Phase E partially implemented: Tushare raw-cache envelopes can be written and indexed into source manifests; forecast normalization/source-count preview commands exist.
- Phase F partially implemented: `quality-auditor tushare-raw-cache` checks raw-cache schema and token/key leakage risk.
- Remaining extension direction: add more public-web fallback adapters only when a specific Tushare permission gap is encountered; broaden live smoke tests after confirming quota/cooldown requirements.

## 1. Goal

Refactor the current data-fetching skills from a relatively coarse BaoStock/AKShare/Tencent-oriented surface into a Tushare-first, skill-owned, auditable data collection layer.

Target outcome:

- use Tushare as the main structured data source for A-share market, financial, valuation, governance, capital-flow, sector/theme, forecast, macro, fund/ETF, convertible-bond, and selected cross-asset data;
- keep scripts and business logic under `.codex/skills/<skill>/scripts` and `.codex/skills/<skill>/src`, following `skill_module_refactor_plan.md`;
- keep `investment_system/core/` for shared project semantics and small connection facades only, not for broad data-source business logic;
- preserve `project_id`, canonical `sector_id`, stock-universe resolution, evidence/source traceability, dry-run defaults, and formal-output safety;
- use `a-stock-data` as a reference for public-web endpoint coverage, ticker normalization, and source-specific rate limits, not as a replacement architecture;
- expand data types without letting transient API rows become unsupported research claims.

## 2. Non-Goals

- Do not turn `a-stock-data` into the primary project skill.
- Do not create a single giant data-fetching skill that bypasses existing workflow skills.
- Do not put broad endpoint implementations under `investment_system/core/data_sources/`.
- Do not write formal research outputs during data-fetch refactor work.
- Do not expose `TUSHARE_TOKEN`, proxy tokens, API keys, cookies, or private URLs in reports, logs, source rows, or examples.
- Do not use AKShare or Eastmoney public-web endpoints as high-frequency sweep sources.
- Do not infer product stage, customer binding, order progress, capacity progress, or investment conclusions from market/financial databases alone.
- Do not delete or move existing outputs or retired wrappers as part of this plan.

## 3. Current Baseline

Current project-local data-related skills:

- `market-data-router`: market data CLI exists, with fallback commands routed through `investment_system/core/data_sources/research_client.py`.
- `financial-data-router`: financial CLI exists, but core collection is still BaoStock/AKShare-oriented.
- `evidence-miner`: has source-manifest, draft, registration, and Tushare cache split commands.
- `forecast-normalizer`: mostly guidance/status only; forecast extraction and Tushare forecast datasets are deferred.
- `sector-research-orchestrator`: top-level workflow still describes old source priority in places.
- `quality-auditor`: checks output/evidence quality, but can be extended to audit new Tushare raw-cache/source metadata.

Known issues:

- Existing source priority still says daily K-line and financial statements are BaoStock/AKShare first, with Tushare as fallback.
- Existing rate-limit guidance uses AKShare's 8-12 seconds plus jitter too broadly; this does not fit Tushare proxy/API behavior or all public-web sources.
- `a-stock-data` has useful endpoint coverage and anti-ban guidance, but it is a large single-file skill without project-aware cache/evidence/gate integration.
- A previous independent Tushare proxy smoke test showed broad Tushare coverage works, while some datasets such as announcements, research reports, and IR Q&A may require additional permissions.

## 4. Design Principles

### Skill-Owned Data Logic

Business data-fetch logic should live in skill modules:

```text
.codex/skills/market-data-router/
  scripts/cli.py
  src/market_data_router/
  src/tushare_data_router/      # shared by data skills via skill src path

.codex/skills/financial-data-router/
  scripts/cli.py
  src/financial_data_router/

.codex/skills/evidence-miner/
  scripts/cli.py
  src/evidence_miner/

.codex/skills/forecast-normalizer/
  scripts/cli.py
  src/forecast_normalizer/
```

`investment_system/core/` may keep:

- project loader and sector/stock resolvers;
- output/evidence/schema/audit contracts;
- `get_tushare_pro()` or equivalent Tushare connection facade;
- shared constants and subprocess/path helpers.

It should not accumulate one module per Tushare endpoint.

### Tushare-First, Not Tushare-Only

Use Tushare first for structured, repeatable datasets. Use other sources when they are stronger for a specific need:

- Tencent direct: fast realtime quote sanity check, PE/PB/market cap fallback.
- Eastmoney public APIs: useful for public reports, hot rankings, concept data, and some funds/flows when Tushare is unavailable or lacks permission.
- CNINFO/official documents: stronger than databases for announcements, business claims, customer/order/capacity evidence.
- `a-stock-data`: reference implementation and public-web fallback catalog.

### Source-Specific Rate Limits

Do not apply one global wait policy to every source.

| Source | Default policy | Rationale |
|---|---|---|
| Tushare proxy/API | serial, default 0.5-1.0s interval plus small jitter; configurable by env/CLI | proxy docs allow reasonable request speed but warn about cooldown; short interval fits paid quota and smoke tests |
| Eastmoney public web | serial only, >=1.0s plus 0.1-0.5s jitter; 1.5-2.0s for batches | follows `a-stock-data` anti-ban model |
| AKShare public web | low-frequency, small-batch only, 8-12s plus jitter when using Eastmoney-like endpoints | previous endpoint failures and anti-ban preference |
| Tencent direct | small batches, modest wait in loops | generally stable, but still avoid tight loops |
| BaoStock | single login session, moderate interval | avoid repeated login/logout and batch churn |
| CNINFO/official web | targeted, low concurrency, cache raw files | primary evidence source; avoid noisy broad search |

### Dry-Run First

Every data skill command should default to preview/dry-run. Live calls require `--fetch`. Cache writes require `--write-cache` or a similarly explicit write flag.

### Raw Cache Before Evidence

API rows should first become raw cache records, then optional source manifest rows, then curated evidence. Do not skip directly from API output to final research prose.

## 5. Tushare Dataset Coverage Map

The following map is based on the Tushare interface research thread and the independent smoke-test results. It should be updated as permissions and project needs change.

### Market Data Router Ownership

| Dataset group | Tushare examples | Purpose |
|---|---|---|
| A-share basics | `stock_basic`, `trade_cal`, `stock_st`, `suspend_d` | universe sanity, status, trading-calendar checks |
| Daily/periodic market data | `daily`, `weekly`, `monthly`, `adj_factor`, `daily_basic`, `bak_daily` | price, returns, valuation, turnover, adjustment factors |
| Realtime/minute | `rt_k`, `rt_min`, `stk_mins` | focused intraday checks; avoid broad minute sweeps |
| Technical/market factors | `stk_factor`, `stk_factor_pro`, `stk_nineturn` | optional market features and technical context |
| Trading behavior | `moneyflow`, `moneyflow_dc`, `top_list`, `top_inst`, `stk_auction`, `stk_limit`, `limit_list_d`, `stk_shock` |资金流、龙虎榜、集合竞价、涨跌停、异常波动 |
| Margin and lending | `margin`, `margin_detail`, `slb_sec` | financing and securities lending |
| Sectors/themes | `index_classify`, `index_member_all`, `ths_index`, `ths_member`, `dc_index`, `dc_member`, `tdx_index`, `dc_concept`, `dc_concept_cons`, `ths_hot`, `dc_hot` | sector/theme membership, heat, and rotation |
| Index/fund/ETF/CB market | `index_daily`, `index_weight`, `fund_daily`, `etf_mins`, `rt_etf_k`, `cb_daily`, `cb_factor_pro` | benchmarks, ETFs, convertible-bond context |

### Financial Data Router Ownership

| Dataset group | Tushare examples | Purpose |
|---|---|---|
| Financial statements | `income`, `balancesheet`, `cashflow` | revenue, profit, assets, liabilities, cash flow |
| Financial indicators | `fina_indicator`, `fina_audit`, `fina_mainbz` | margins, ROE, EPS, audit, segment revenue |
| Company profile | `stock_company`, `stk_managers`, `stk_rewards` | company metadata, management, compensation/shareholding |
| Holders and equity | `top10_holders`, `top10_floatholders`, `stk_holdernumber`, `stk_holdertrade`, `share_float`, `pledge_detail` | holders, holder count, unlocks, pledges |
| Dividends and repurchase | `dividend`, `repurchase` | capital return and share count changes |
| Valuation support | `daily_basic`, `daily`, `adj_factor` | PE TTM, PB, market cap, close price |

### Evidence Miner Ownership

| Dataset group | Tushare examples | Purpose |
|---|---|---|
| Announcements | `anns_d` | announcement index; may require separate permission |
| Research reports | `research_report` | report metadata; may require separate permission |
| Broker forecast/source rows | `report_rc` | forecast source rows and institution coverage |
| Institutional surveys | `stk_surv` | IR/survey evidence index |
| Interactive Q&A | `irm_qa_sh`, `irm_qa_sz` | exchange Q&A; may require separate permission |
| News and policies | `news`, `cctv_news`, `major_news`, `npr`, `monetary_policy` | weak or contextual evidence unless curated |

### Forecast Normalizer Ownership

| Dataset group | Tushare examples | Purpose |
|---|---|---|
| Broker forecasts | `report_rc` | EPS, PE, institution report date, forecast source count |
| Research report metadata | `research_report` | report title/org/author/date source trace |
| User-provided/curated forecast evidence | evidence YAML | keep public-page or user-supplied forecasts labeled |

### Macro and Cross-Asset Context

Usually secondary context, not core sector evidence:

- macro: `cn_gdp`, `cn_cpi`, `cn_ppi`, `cn_pmi`, `cn_m`, `sf_month`, `eco_cal`;
- rates: `yc_cb`, `shibor`, `shibor_lpr`, `libor`, `hibor`, `repo_daily`;
- futures/options: `fut_basic`, `fut_daily`, `ft_mins`, `opt_basic`, `opt_daily`, `opt_mins`;
- HK/US/AH: `hk_basic`, `hk_daily`, `hk_mins`, `us_basic`, `us_daily`, `stk_ah_comparison`.

## 6. Proposed Command Surface

### Shared Tushare Dataset Command

Create a skill-local implementation that can be delegated from multiple skills:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\market-data-router\scripts\cli.py tushare-fetch --group market --dataset daily --project tech_ai_semiconductor --sector-id <sector_id>
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\market-data-router\scripts\cli.py tushare-fetch --group market --dataset daily --code 000001.SZ --fetch
```

Behavior:

- without `--dataset`: list supported datasets for a group;
- without `--fetch`: show planned requests and parameters only;
- with `--fetch`: call Tushare with configured token/http URL;
- with `--write-cache`: write raw cache under `investment_system/data/raw/tushare/<dataset>/<date>/`;
- never print token or private config.

### Market Data Router

Add or revise commands:

- `tushare-fetch --group market`
- `daily-kline`: route to Tushare first; BaoStock/Tencent become fallback or compatibility mode.
- `daily-basic`
- `moneyflow`
- `dragon-tiger`
- `margin`
- `limit-list`
- `sector-theme`
- `index-daily`
- `fund-etf-daily`
- `convertible-bond-daily`

### Financial Data Router

Add or revise commands:

- `tushare-fetch --group financial`
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

Existing `profit` should either become a Tushare-first compatibility command or be renamed/documented as BaoStock compatibility.

### Evidence Miner

Add or revise commands:

- `tushare-fetch --group evidence`
- `tushare-source-manifest`
- `announcements-index`
- `research-report-index`
- `survey-index`
- `irm-qa-index`
- keep `split-tushare-cache`, but allow it to consume the new raw-cache layout.

Evidence outputs must remain manifest/draft-first and should not register automatically.

### Forecast Normalizer

Add commands:

- `tushare-fetch --group forecast`
- `report-rc`
- `normalize-forecast-fields`
- `audit-forecast-source-count`

Forecast data must label source type: Tushare broker forecast row, public report metadata, user-provided forecast, single-source estimate, or unavailable.

## 7. Raw Cache Contract

Each fetched raw file should have a stable envelope:

```json
{
  "source": "tushare",
  "dataset": "daily_basic",
  "api_name": "daily_basic",
  "project_id": "tech_ai_semiconductor",
  "sector_id": "high_speed_copper_connector",
  "stock": {
    "ts_code": "000001.SZ",
    "stock_code": "000001",
    "market": "SZ",
    "stock_name": "平安银行"
  },
  "params": {},
  "fields": [],
  "fetched_at": "2026-06-29T00:00:00",
  "rate_limit": {
    "min_interval_seconds": 0.7,
    "jitter_seconds": 0.2
  },
  "status": "OK",
  "row_count": 0,
  "records": [],
  "error": null
}
```

Path convention:

```text
investment_system/data/raw/tushare/<dataset>/<run_date>/<ts_code_or_all>.json
investment_system/data/raw/tushare/diagnostics/<run_date>/<check_name>.json
```

If a dataset is permission-limited, the raw record should preserve:

- dataset name;
- params;
- failure type;
- sanitized error message;
- no token.

## 8. Source and Evidence Promotion Rules

Tushare data can support:

- market facts;
- valuation fields;
- financial statement fields;
- shareholder/capital-structure fields;
- trading heat and risk context;
- forecast metadata when source rows are available.

Tushare data cannot by itself prove:

- product stage;
- customer/order binding;
- capacity progress;
- supplier/customer qualification;
- technology roadmap;
- formal investment conclusion.

Those must be supported by annual reports, announcements, IR records, exchange Q&A, policy files, or broker-report excerpts with explicit source IDs.

## 9. a-stock-data Integration Role

Use `a-stock-data` for three things:

1. Public-web fallback catalog:
   - Eastmoney reportapi/PDF;
   - Eastmoney concept/fund-flow/hot rank;
   - CNINFO orgId and announcement patterns;
   - Tencent quote field mapping;
   - THS hot/reason and EPS page patterns.

2. Rate-limit design:
   - Eastmoney serial-only request model;
   - per-source wait policy instead of a single global wait;
   - no public-web concurrency in batch loops.

3. Ticker normalization patterns:
   - support `000001`, `000001.SZ`, `SZ000001`, `sh600519`;
   - keep Tushare `ts_code` distinct from Tencent/Eastmoney/BaoStock symbol formats.

Do not copy:

- its single huge `SKILL.md` architecture;
- direct final-report examples;
- endpoints into core without skill ownership;
- any claims that are not validated in the current environment.

## 10. Implementation Phases

### Phase A: Plan and Audit Only

- Create and maintain this plan file.
- Inventory current data commands and references.
- Map each Tushare dataset to owner skill.
- No implementation changes except plan/reference updates.

Exit criteria:

- plan accepted;
- current modified files and pre-existing changes clearly separated;
- no new fetch code required in this phase.

### Phase B: Skill-Local Tushare Dataset Catalog

- Add a `tushare_data_router` skill-local module under a skill `src` directory.
- Provide dataset catalog and dry-run planning.
- Add `tushare-fetch` command aliases from market, financial, evidence, and forecast skills.
- Keep default no-fetch behavior.

Validation:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\market-data-router\scripts\cli.py tushare-fetch --group market --format json
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\financial-data-router\scripts\cli.py tushare-fetch --group financial --format json
```

### Phase C: Small Tushare Smoke Fetches

- Use `--fetch --limit 1 --rows 3` only.
- Test representative datasets:
  - `stock_basic`;
  - `daily`;
  - `daily_basic`;
  - `income`;
  - `balancesheet`;
  - `cashflow`;
  - `fina_indicator`;
  - `moneyflow`;
  - `report_rc`;
  - one permission-sensitive evidence dataset such as `anns_d` or `research_report`.
- Record permission failures as expected data-access findings, not code failures.

Validation:

- no token printed;
- no formal output written;
- no high-frequency loop;
- raw cache only when `--write-cache` is explicitly passed.

### Phase D: Replace Old Priority Guidance

Update active skill guidance:

- market route order becomes Tushare-first for structured datasets;
- BaoStock/Tencent become fallback/compatibility or focused sanity checks;
- AKShare becomes low-frequency fallback only;
- a-stock-data public-web endpoints become explicitly fallback/reference, not primary project source.

Files likely to update:

- `.codex/skills/market-data-router/SKILL.md`;
- `.codex/skills/market-data-router/references/contract.md`;
- `.codex/skills/financial-data-router/SKILL.md`;
- `.codex/skills/financial-data-router/references/contract.md`;
- `.codex/skills/evidence-miner/SKILL.md`;
- `.codex/skills/evidence-miner/references/contract.md`;
- `.codex/skills/forecast-normalizer/SKILL.md`;
- `.codex/skills/sector-research-orchestrator/references/data_sources.md`;
- `investment_system/config/data_sources.example.toml`.

### Phase E: Evidence Manifest Integration

- Teach `evidence-miner` to create source manifests from the new Tushare raw cache envelope.
- Keep draft evidence blocked until manual curation.
- Add missing-data logging for permission-limited datasets.

Validation:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\evidence-miner\scripts\cli.py split-tushare-cache --project tech_ai_semiconductor --sector-id <sector_id> --cache-path <cache>
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py evidence-gate --project tech_ai_semiconductor --sector-id <sector_id>
```

### Phase F: Writer and Auditor Alignment

- Update writer adapters to understand Tushare raw/source rows as primary market/financial data.
- Update quality auditor to check:
  - Tushare provider identity;
  - no token leakage;
  - source period labels;
  - actual/TTM/forecast separation;
  - permission failure records.

Validation:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py pipeline-readiness --project tech_ai_semiconductor
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py validate-outputs --project tech_ai_semiconductor
```

## 11. Validation Gate Matrix

Minimum checks for any phase that changes code:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe -m py_compile <touched .py files>
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py pipeline-readiness --project tech_ai_semiconductor
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py validate-outputs --project tech_ai_semiconductor
```

Data-specific gates:

| Area | Gate |
|---|---|
| Tushare config | `market-data-router tushare-ping` or `financial-data-router tushare-ping` |
| Dataset catalog | dry-run `tushare-fetch --group <group> --format json` |
| Live fetch | one-symbol or one-sector `--limit 1 --rows 3 --fetch` |
| Cache write | explicit `--write-cache`, then inspect raw path and token absence |
| Evidence promotion | evidence manifest/draft/curation gates |
| Output safety | no formal-root writes unless explicitly requested and gates pass |

## 12. Open Questions

- Should the project update `.env.local` to the new Tushare proxy token/domain, or keep proxy tests isolated until the first implementation phase?
- Which Tushare datasets have paid/independent permissions under the current token and should be marked unavailable by default?
- Should `market-data-router daily-kline` be changed in place to Tushare-first, or should a new `tushare-daily` command be introduced first and then made default after validation?
- Should permission-limited evidence datasets such as `anns_d`, `research_report`, and `irm_qa_*` stay in `evidence-miner` as planned-but-disabled commands until access is available?
- Should short-term trading datasets such as `limit_list_d`, `top_list`, `moneyflow`, and hot ranks be excluded from formal research outputs by policy, or allowed as low-confidence trading-heat context?

## 13. Update Rules for This File

- Update this file before starting each implementation phase.
- Record actual command outputs or audit file links after each phase completes.
- Mark a dataset as active only after dry-run, one-symbol fetch, cache inspection, and token-leak check pass.
- Mark permission-limited datasets explicitly instead of deleting them from the roadmap.
- Do not use this file to authorize deletion of any file.
- Do not treat this file as proof that data has been collected or validated.
