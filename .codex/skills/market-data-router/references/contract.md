# Market Data Contract

## Inputs

- `sub_theme`
- stock list with `code`, `market`, `set_code`, `name`
- run date

## Outputs

- Raw daily K-line JSON:
  `investment_system/data/raw/baostock/daily_kline/<date>/<code>.json`
- Optional AKShare raw quote or fund-flow JSON:
  `investment_system/data/raw/akshare/<dataset>/<date>/<code>.json`
- Optional Tushare raw JSON or CSV:
  `investment_system/data/raw/tushare/<dataset>/<date>/<code>.json`
- Processed fields:
  `latest_price`, `pct_change_1m`, `pct_change_3m`, `pct_change_6m`, `turnover_value_20d_avg`, `relative_strength_vs_index`

## Acceptance

- At least one daily K-line source succeeds for every representative company.
- Last available trading date is explicitly known; do not imply calendar date equals data date.
- AKShare failures from Eastmoney/proxy endpoints are recorded, not retried aggressively.
- Tushare HTTP-bridge or proxy failures are recorded separately from token/auth failures.
- Disabled Guosen skills are not treated as available fallback sources.
