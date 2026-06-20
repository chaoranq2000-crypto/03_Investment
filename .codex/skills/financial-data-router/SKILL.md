---
name: financial-data-router
description: Collects and normalizes A-share financial data for sector research, including revenue, net profit, gross margin, net margin, EPS, total shares, PE TTM, PS TTM, and low-frequency financial statements using BaoStock, AKShare, Tushare, and company reports. Use when financial fields in research tables need refreshing, auditing, or repair.
---

# Financial Data Router

Use this as the financial-data layer. It should provide normalized fields, not investment conclusions.

## Entry Points

- Primary code: `investment_system/scripts/research_client.py`
- Tushare bridge: `investment_system/pipelines/tushare_client.py`
- Standard pipeline: `investment_system/pipelines/run_research.py`
- Cleanup/derived metrics: `investment_system/pipelines/cleanup_outputs.py`
- Contract: read `references/contract.md` before adding financial fields.

## Route Order

1. Financial statements: BaoStock -> AKShare -> Tushare -> company reports.
2. Profit indicators and margins: BaoStock primary, then Tushare/AKShare, then company reports.
3. PE TTM: latest close / `epsTTM`.
4. Market cap: latest close * `totalShare`.
5. PS TTM: market cap / latest full-year revenue.

## Rules

- Keep units explicit: yuan in raw data, `亿` or `亿元` in output.
- Never mix BaoStock quarterly rows with annual-report values without noting the source.
- If annual-report values override database values, record the conflict or source choice.
- Use `get_tushare_pro()` for Tushare access; do not set `_DataApi__http_url` in scattered scripts.
- Do not call disabled Guosen `gs-*` skills or require `GS_API_KEY`.
- Do not write API keys into logs, CSVs, cards, or evidence YAML.
