# Forecast Contract

## Inputs

- Current market cap and latest close from market-data-router.
- Share count/EPS from financial-data-router.
- Forecast values from user-provided data, public broker reports, verifiable 同花顺/Choice-style web pages, or curated evidence YAML. Do not assume Wind or iFind access.

## Outputs

- `revenue_2026E`, `revenue_2027E`
- `net_profit_2026E`, `net_profit_2027E`
- `pe_2026E`, `pe_2027E`
- `peg_2026E`
- `institution_forecast_change`

## Acceptance

- Every forward-looking field has a source label.
- Consensus, average, median, public-page, user-provided, judgment, and single-broker forecasts are not conflated.
- Extreme valuation calls are supported by both forward PE and growth context.
