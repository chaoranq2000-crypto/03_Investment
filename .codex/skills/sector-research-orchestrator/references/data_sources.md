# Data Sources

Use `market-data-router`, `financial-data-router`, `evidence-miner`, and `forecast-normalizer` for source-specific work. This file is the top-level source policy.

## Configuration

- Config example: `investment_system/config/data_sources.example.toml`.
- Local private override: `investment_system/config/data_sources.local.toml`.
- Environment example: `investment_system/config/.env.example`.
- Local real secrets: `investment_system/config/.env.local`.
- Project Python runtime: `C:\Projects\03_Investment\.conda\investment-system\python.exe`.
- The TOML config is for provider diagnostics, env names, and runtime defaults. Tushare endpoint coverage lives in `.codex/skills/market-data-router/src/tushare_data_router/datasets.py`.
- Never write `.env.local`, real tokens, or API keys into reports, logs, evidence excerpts, candidate cards, or formal outputs.

## Priority

- Structured market data: Tushare first for A-share basics, daily/weekly/monthly data, adjustment factors, daily_basic, moneyflow, margin, dragon-tiger, limit lists, index/fund/ETF/CB data, and theme heat.
- Financial low-frequency data: Tushare first for statements, indicators, main-business composition, holders, equity changes, dividends, repurchase, and valuation support; company filings override database rows when conflict is documented.
- Realtime quotes and quick sanity checks: Tencent direct for focused PE/PB/market-cap/quote checks; Tushare realtime/minute only for focused pulls.
- Business exposure, customers, orders, capacity: company reports, announcements, IR records, exchange Q&A.
- Forecasts: Tushare `report_rc` and report metadata when available, plus user-provided data, publicly accessible broker reports, and verifiable 同花顺/Choice-style web pages. Do not assume Wind or iFind access.
- Public-web fallbacks: use `investment_system/docs/data_sources/a-stock-data/` as a reference for Tencent, Eastmoney, CNINFO, Sina, Tonghuashun, and iwencai endpoint patterns when Tushare has no permission, no coverage, or weaker freshness.
- When a public interface and a primary company document conflict, preserve both records and let the candidate/report disclose the conflict instead of silently choosing the convenient value.

## Rate Limits

- Use `investment_system.core.data_sources.research_client` instead of direct ad hoc requests.
- Use `market-data-router tushare-ping` or `financial-data-router tushare-ping` for Tushare diagnostics so the configured HTTP bridge, token, and proxy-clearing policy are applied through the shared facade.
- Use `tushare-fetch` for new structured data pulls. It is dry-run by default; `--fetch` performs live calls, `--write-cache` writes raw envelopes, and `--write-manifest` writes source-manifest rows.
- Tushare proxy/API calls: default serial 0.7s + 0-0.2s jitter from `data_sources.example.toml`, configurable by `--interval`/`--jitter` or `TUSHARE_REQUEST_INTERVAL_SECONDS`/`TUSHARE_REQUEST_JITTER_SECONDS`.
- Eastmoney public-web fallbacks copied or adapted from `investment_system/docs/data_sources/a-stock-data/`: serial only, session reuse, at least 1s + jitter; 1.5-2s for batches.
- AKShare public web calls: wait 8-12 seconds between calls by default.
- Tencent direct calls: use small batches and add waiting in looped jobs.
- BaoStock: use one session for a batch and avoid repeated login/logout.
- Tushare: keep `TUSHARE_TOKEN`, `TUSHARE_HTTP_URL`, and `TUSHARE_DISABLE_PROXY` in `investment_system/config/.env.local`; never echo the token into logs or reports.

## Config Checks

Use read-only checks before broad collection:

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" -m investment_system.core.data_sources.diagnostics
```

Use the Tushare ping only when Tushare connectivity matters:

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\market-data-router\scripts\cli.py tushare-ping
```

Use dry-run data routing previews before focused pulls:

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\market-data-router\scripts\cli.py daily-kline --project tech_ai_semiconductor --sector-id <sector_id>
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\market-data-router\scripts\cli.py tushare-fetch --dataset daily --project tech_ai_semiconductor --sector-id <sector_id>
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\financial-data-router\scripts\cli.py profit --project tech_ai_semiconductor --sector-id <sector_id>
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\financial-data-router\scripts\cli.py tushare-fetch --dataset income --project tech_ai_semiconductor --sector-id <sector_id>
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\financial-data-router\scripts\cli.py normalize-financials --project tech_ai_semiconductor --sector-id <sector_id>
```

Pass `--fetch` only for focused live pulls. These commands write to stdout by default and do not write raw-data cache files.

## Failure Handling

- If a data source fails, save the failure type in raw diagnostics.
- Do not infer that an API key is invalid from TLS/proxy errors.
- Do not infer that the Tushare token is invalid from HTTP-bridge or proxy failures; verify the bridge with `market-data-router tushare-ping` or `financial-data-router tushare-ping`.
- Guosen skills are disabled; do not route tasks to `gs-*` skills or require `GS_API_KEY`.
- Do not silently replace a high-priority source with a low-priority source; record the fallback in `数据来源索引.csv`.
- If all configured interfaces fail for a required field, search the web for primary or high-quality secondary evidence.
- Web evidence must still become a source row with `source_url`, source date, excerpt, supported fields, and confidence.
- If web evidence cannot be indexed by URL or local cache path, treat it as unresolved and list it in `缺失数据清单.md`.
- Keep durable manual evidence in `investment_system/research/evidence/` so final outputs can be regenerated.
- Seed documents and context-only notes are not evidence. Promote only manually curated facts with source ID, evidence ID, source date, excerpt, claim, limitation, and missing fields.
