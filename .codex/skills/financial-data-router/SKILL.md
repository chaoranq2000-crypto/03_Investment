---
name: financial-data-router
description: Collects and normalizes A-share financial data for sector research, including revenue, net profit, gross margin, net margin, EPS, total shares, PE TTM, PS TTM, and low-frequency financial statements using BaoStock, AKShare, Tushare, and company reports. Use when financial fields in research tables need refreshing, auditing, or repair.
---

# Financial Data Router

Use this as the financial-data layer. It should provide normalized fields, not investment conclusions.

## Entry Points

- Primary code: `investment_system/scripts/research_client.py`
- Skill CLI:
  - `.codex/skills/financial-data-router/scripts/cli.py profit --project tech_ai_semiconductor --sector-id <sector_id>`
  - `.codex/skills/financial-data-router/scripts/cli.py financial-indicator --code <6_digit_code>`
  - `.codex/skills/financial-data-router/scripts/cli.py normalize-financials --project tech_ai_semiconductor --sector-id <sector_id>`
  - `.codex/skills/financial-data-router/scripts/cli.py tushare-ping`
- Standard pipeline: `investment_system/pipelines/run_research.py`
- Derived metrics should be normalized before output generation and checked through `.codex/skills/quality-auditor/scripts/cli.py validate-outputs`
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
- CLI data commands are dry-run by default; pass `--fetch` only for focused live pulls.
