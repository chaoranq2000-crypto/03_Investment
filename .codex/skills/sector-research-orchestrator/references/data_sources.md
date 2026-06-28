# Data Sources

Use `market-data-router`, `financial-data-router`, `evidence-miner`, and `forecast-normalizer` for source-specific work. This file is the top-level source policy.

## Configuration

- Config example: `investment_system/config/data_sources.example.toml`.
- Local private override: `investment_system/config/data_sources.local.toml`.
- Environment example: `investment_system/config/.env.example`.
- Local real secrets: `investment_system/config/.env.local`.
- Project Python runtime: `C:\Projects\03_Investment\.conda\investment-system\python.exe`.
- Never write `.env.local`, real tokens, or API keys into reports, logs, evidence excerpts, candidate cards, or formal outputs.

## Priority

- Daily kline: BaoStock -> Tencent direct -> AKShare -> Tushare.
- Financial low-frequency data: BaoStock -> AKShare -> Tushare -> company reports.
- Realtime quotes and fund flow: AKShare or Tushare when available, only for focused symbols.
- Business exposure, customers, orders, capacity: company reports, announcements, IR records, exchange Q&A.
- Forecasts: user-provided data, publicly accessible broker reports, and verifiable 同花顺/Choice-style web pages. Do not assume Wind or iFind access.
- When a public interface and a primary company document conflict, preserve both records and let the candidate/report disclose the conflict instead of silently choosing the convenient value.

## Rate Limits

- Use `research_client.py` instead of direct ad hoc requests.
- Use `investment_system/pipelines/tushare_client.py` for Tushare so the configured HTTP bridge, token, and proxy-clearing policy are applied.
- AKShare public web calls: wait 8-12 seconds between calls by default.
- Tencent direct calls: use small batches and add waiting in looped jobs.
- BaoStock: use one session for a batch and avoid repeated login/logout.
- Tushare: keep `TUSHARE_TOKEN`, `TUSHARE_HTTP_URL`, and `TUSHARE_DISABLE_PROXY` in `investment_system/config/.env.local`; never echo the token into logs or reports.

## Config Checks

Use read-only checks before broad collection:

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\scripts\check_data_sources.py
```

Use the Tushare ping only when Tushare connectivity matters:

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\pipelines\tushare_client.py --ping
```

## Failure Handling

- If a data source fails, save the failure type in raw diagnostics.
- Do not infer that an API key is invalid from TLS/proxy errors.
- Do not infer that the Tushare token is invalid from HTTP-bridge or proxy failures; verify the bridge with `tushare_client.py --ping`.
- Guosen skills are disabled; do not route tasks to `gs-*` skills or require `GS_API_KEY`.
- Do not silently replace a high-priority source with a low-priority source; record the fallback in `数据来源索引.csv`.
- If all configured interfaces fail for a required field, search the web for primary or high-quality secondary evidence.
- Web evidence must still become a source row with `source_url`, source date, excerpt, supported fields, and confidence.
- If web evidence cannot be indexed by URL or local cache path, treat it as unresolved and list it in `缺失数据清单.md`.
- Keep durable manual evidence in `investment_system/research/evidence/` so final outputs can be regenerated.
- Seed documents and context-only notes are not evidence. Promote only manually curated facts with source ID, evidence ID, source date, excerpt, claim, limitation, and missing fields.
