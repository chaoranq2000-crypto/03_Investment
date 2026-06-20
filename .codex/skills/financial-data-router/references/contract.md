# Financial Data Contract

## Inputs

- Company code and market.
- Years/quarters required for the report.
- Latest market close from `market-data-router`.

## Outputs

- Raw profit JSON:
  `investment_system/data/raw/baostock/profit/<date>/<code>.json`
- Optional Tushare financial JSON or CSV:
  `investment_system/data/raw/tushare/<dataset>/<date>/<code>.json`
- Company-table fields:
  `revenue_2024`, `revenue_2025`, `net_profit_2024`, `net_profit_2025`, `gross_margin_latest`, `net_margin_latest`, `pe_ttm`, `ps_ttm`, `market_cap`

## Acceptance

- Revenue and profit units are consistent across rows.
- `pe_ttm` and `ps_ttm` are filled or listed in the missing-data log.
- Any database/report mismatch is traceable to source rows or a conflict note.
- Tushare fallback rows identify Tushare as the source and do not hide bridge/proxy failures as missing business data.
