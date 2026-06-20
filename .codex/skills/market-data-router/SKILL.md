---
name: market-data-router
description: Routes A-share market data collection across BaoStock, Tencent direct, AKShare, and Tushare with project rate limits and raw-data caching. Use when fetching or refreshing daily K-line data, latest prices, returns, turnover, relative strength, realtime quotes, fund flow, or when diagnosing BaoStock/AKShare/Tushare market-data failures in C:\Projects\03_Investment.
---

# Market Data Router

Use this as the market-data layer for sector research. Keep collection and analysis separate.

## Entry Points

- Primary code: `investment_system/scripts/research_client.py`
- Tushare bridge: `investment_system/pipelines/tushare_client.py`
- Standard pipeline: `investment_system/pipelines/run_research.py`
- Diagnostics: `investment_system/scripts/validate_research_client.py`
- Contract: read `references/contract.md` when changing routes or rate limits.

## Route Order

1. Daily K-line: BaoStock -> Tencent direct -> AKShare -> Tushare.
2. Realtime quotes and fund flow: AKShare or Tushare when available, only for focused symbols.
3. Index daily data: AKShare Sina endpoint when available; use Tushare as configured fallback; otherwise cached raw files.

## Rules

- Use `ResearchClient`; do not create ad hoc request loops.
- Do not call disabled Guosen `gs-*` skills or require `GS_API_KEY`.
- BaoStock must use one batch session and avoid repeated login/logout.
- AKShare public-web calls must wait 8-12 seconds with jitter and stay small-batch.
- Tushare calls must go through `get_tushare_pro()` so `TUSHARE_HTTP_URL` and proxy clearing are honored.
- Tencent direct calls must be rate-limited in loops.
- Save raw data under `investment_system/data/raw/<source>/<dataset>/<date>/`.
- Record source fallback or failures in `数据来源索引.csv` or diagnostics.
