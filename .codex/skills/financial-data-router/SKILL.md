---
name: financial-data-router
description: Collects and normalizes A-share financial data for sector research through a Tushare-first workflow, including revenue, net profit, gross margin, net margin, EPS, total shares, PE TTM, PS TTM, holders, dividends, repurchase, and low-frequency financial statements. Use when financial fields in research tables need refreshing, auditing, or repair.
---

# Financial Data Router

Use this as the financial-data layer. It should provide normalized fields, not investment conclusions.

## Entry Points

- Primary fallback client: `investment_system/core/data_sources/research_client.py`
- Skill CLI:
  - `.codex/skills/financial-data-router/scripts/cli.py tushare-fetch`
  - `.codex/skills/financial-data-router/scripts/cli.py tushare-fetch --dataset income --code 000001.SZ --period 20250331`
  - `.codex/skills/financial-data-router/scripts/cli.py tushare-fetch --dataset fina_indicator --project tech_ai_semiconductor --sector-id <sector_id>`
  - `.codex/skills/financial-data-router/scripts/cli.py income --code <ts_code> --period <YYYYMMDD>`
  - `.codex/skills/financial-data-router/scripts/cli.py balancesheet --code <ts_code> --period <YYYYMMDD>`
  - `.codex/skills/financial-data-router/scripts/cli.py cashflow --code <ts_code> --period <YYYYMMDD>`
  - `.codex/skills/financial-data-router/scripts/cli.py fina-indicator --code <ts_code> --period <YYYYMMDD>`
  - `.codex/skills/financial-data-router/scripts/cli.py main-business --code <ts_code> --period <YYYYMMDD>`
  - `.codex/skills/financial-data-router/scripts/cli.py holders --code <ts_code>`
  - `.codex/skills/financial-data-router/scripts/cli.py share-float --code <ts_code>`
  - `.codex/skills/financial-data-router/scripts/cli.py dividend --code <ts_code>`
  - `.codex/skills/financial-data-router/scripts/cli.py repurchase --code <ts_code>`
  - `.codex/skills/financial-data-router/scripts/cli.py valuation-snapshot --code <ts_code>`
  - `.codex/skills/financial-data-router/scripts/cli.py profit --project tech_ai_semiconductor --sector-id <sector_id>`
  - `.codex/skills/financial-data-router/scripts/cli.py financial-indicator --code <6_digit_code>`
  - `.codex/skills/financial-data-router/scripts/cli.py normalize-financials --project tech_ai_semiconductor --sector-id <sector_id>`
  - `.codex/skills/financial-data-router/scripts/cli.py tushare-ping`
- Derived metrics should be normalized before output generation and checked through `.codex/skills/quality-auditor/scripts/cli.py validate-outputs`
- Contract: read `references/contract.md` before adding financial fields.

## Route Order

1. Financial statements and indicators: Tushare first for `income`, `balancesheet`, `cashflow`, `fina_indicator`, and `fina_mainbz`.
2. Holders, equity, dividends, and repurchase: Tushare first for holder/share/dividend/repurchase datasets.
3. Company reports remain the strongest source when database rows conflict with primary filings.
4. BaoStock/AKShare commands remain focused fallback surfaces for source-specific gaps.
5. PE TTM: latest close / `epsTTM`.
6. Market cap: latest close * `totalShare`.
7. PS TTM: market cap / latest full-year revenue.

## Rules

- Keep units explicit: yuan in raw data, `亿` or `亿元` in output.
- Never mix database quarterly rows with annual-report values without noting the source and period.
- If annual-report values override database values, record the conflict or source choice.
- Use `get_tushare_pro()` for Tushare access; do not set `_DataApi__http_url` in scattered scripts.
- Tushare calls are dry-run by default through `tushare-fetch`; use `--fetch` for live calls and `--write-cache` for raw envelopes. Request pacing defaults come from the shared runtime data-source config unless CLI/env overrides are provided.
- Do not call disabled Guosen `gs-*` skills or require `GS_API_KEY`.
- Do not write API keys into logs, CSVs, cards, or evidence YAML.
- CLI data commands are dry-run by default; pass `--fetch` only for focused live pulls.
