# Data Sources

## Priority

- Daily kline: BaoStock -> Tencent direct -> AKShare -> Guosen.
- Financial low-frequency data: Guosen -> BaoStock -> AKShare -> company reports.
- Realtime quotes and fund flow: Guosen -> AKShare, but only for focused symbols.
- Business exposure, customers, orders, capacity: company reports, announcements, IR records, exchange Q&A.
- Forecasts: Wind/同花顺/iFind/券商研报; record institution count and date.

## Rate Limits

- Use `research_client.py` instead of direct ad hoc requests.
- AKShare public web calls: wait 8-12 seconds between calls by default.
- Tencent direct calls: use small batches and add waiting in looped jobs.
- BaoStock: use one session for a batch and avoid repeated login/logout.

## Failure Handling

- If a data source fails, save the failure type in raw diagnostics.
- Do not infer that an API key is invalid from TLS/proxy errors.
- Do not silently replace a high-priority source with a low-priority source; record the fallback in `数据来源索引.csv`.
