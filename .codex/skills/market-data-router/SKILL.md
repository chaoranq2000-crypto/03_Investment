---
name: market-data-router
description: Routes A-share market data collection through a Tushare-first project workflow, with Tencent/BaoStock/AKShare/public-web fallbacks, source-specific rate limits, and raw-data caching. Use when fetching or refreshing daily K-line data, latest prices, returns, turnover, relative strength, realtime quotes, fund flow, theme heat, or when diagnosing data-source failures in C:\Projects\03_Investment.
---

# Market Data Router

Use this as the market-data layer for sector research. Keep collection and analysis separate.

## Entry Points

- Primary fallback client: `investment_system/core/data_sources/research_client.py`
- Skill CLI:
  - `.codex/skills/market-data-router/scripts/cli.py tushare-fetch`
  - `.codex/skills/market-data-router/scripts/cli.py tushare-fetch --dataset daily --code 000001.SZ`
  - `.codex/skills/market-data-router/scripts/cli.py tushare-fetch --dataset daily_basic --project tech_ai_semiconductor --sector-id <sector_id>`
  - `.codex/skills/market-data-router/scripts/cli.py daily-kline --project tech_ai_semiconductor --sector-id <sector_id>`
  - `.codex/skills/market-data-router/scripts/cli.py daily-basic --project tech_ai_semiconductor --sector-id <sector_id>`
  - `.codex/skills/market-data-router/scripts/cli.py moneyflow --code <ts_code>`
  - `.codex/skills/market-data-router/scripts/cli.py dragon-tiger --trade-date <YYYYMMDD>`
  - `.codex/skills/market-data-router/scripts/cli.py margin --code <ts_code>`
  - `.codex/skills/market-data-router/scripts/cli.py limit-list --trade-date <YYYYMMDD>`
  - `.codex/skills/market-data-router/scripts/cli.py sector-theme --trade-date <YYYYMMDD>`
  - `.codex/skills/market-data-router/scripts/cli.py fund-etf-daily --code 510300.SH`
  - `.codex/skills/market-data-router/scripts/cli.py convertible-bond-daily --code <cb_ts_code>`
  - `.codex/skills/market-data-router/scripts/cli.py tencent-daily --code <6_digit_code> --market SZ`
  - `.codex/skills/market-data-router/scripts/cli.py fund-flow --stock <6_digit_code>`
  - `.codex/skills/market-data-router/scripts/cli.py index-daily --symbol sh000001`
  - `.codex/skills/market-data-router/scripts/cli.py stock-info`
  - `.codex/skills/market-data-router/scripts/cli.py tushare-ping`
- Diagnostics: `python -m investment_system.core.data_sources.diagnostics`
- Contract: read `references/contract.md` when changing routes or rate limits.

## Route Order

1. Structured market data: Tushare first for daily, daily_basic, adjustment factor, moneyflow, margin, dragon-tiger, limit-list, index/fund/CB, and theme heat datasets.
2. Fast realtime sanity checks: Tencent direct when a focused quote/PE/PB/market-cap check is enough.
3. BaoStock/AKShare: source fallback for small-batch public-web gaps.
4. Public-web fallbacks from `a-stock-data`: only for unique capabilities Tushare lacks or lacks permission for; keep source-specific anti-ban limits.

## Rules

- Prefer `tushare-fetch` for new structured market pulls. Use `ResearchClient` commands only for focused datasource diagnostics or source-specific gaps.
- Do not call disabled Guosen `gs-*` skills or require `GS_API_KEY`.
- BaoStock must use one batch session and avoid repeated login/logout.
- Tushare proxy/API calls default to the runtime config (`data_sources.example.toml` unless locally overridden); override with `--interval`, `--jitter`, or env only when the purchased quota allows it.
- Eastmoney public-web calls copied or adapted from `a-stock-data` must be serial, session-reused, and wait at least 1s + jitter; use 1.5-2s for batches.
- AKShare public-web calls must wait 8-12 seconds with jitter and stay small-batch.
- Tushare calls must go through `get_tushare_pro()` so `TUSHARE_HTTP_URL` and proxy clearing are honored.
- Tencent direct calls must be rate-limited in loops.
- Save Tushare raw envelopes under `investment_system/data/raw/tushare/<dataset>/<date>/`.
- Record source fallback or failures in `数据来源索引.csv` or diagnostics.
- CLI data commands are dry-run by default; pass `--fetch` only for focused live pulls.
- Cache writes require `--write-cache`; source-manifest writes require `--write-manifest`.
