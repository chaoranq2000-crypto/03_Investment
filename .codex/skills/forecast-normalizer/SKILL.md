---
name: forecast-normalizer
description: Normalizes institution forecasts for A-share sector research, including 2026E/2027E revenue, net profit, EPS, PE, PEG, forecast source count, report date, and forecast-change notes. Use when broker reports, user-provided forecasts, verifiable public forecast pages, or valuation-forward fields need to be filled or audited; do not assume Wind or iFind access.
---

# Forecast Normalizer

Use this as the forecast and forward-valuation layer.

## Entry Points

- Tushare forecast fetcher: `.codex/skills/forecast-normalizer/scripts/cli.py tushare-fetch`
- Tushare broker forecast rows: `.codex/skills/forecast-normalizer/scripts/cli.py tushare-fetch --dataset report_rc --code <ts_code>`
- Alias: `.codex/skills/forecast-normalizer/scripts/cli.py report-rc --code <ts_code>`
- Forecast normalization preview: `.codex/skills/forecast-normalizer/scripts/cli.py normalize-forecast-fields --project <project_id> --sector-id <sector_id>`
- Forecast source-count audit: `.codex/skills/forecast-normalizer/scripts/cli.py audit-forecast-source-count --cache-path <json>`
- Evidence YAML: `investment_system/research/evidence/`
- Company table: resolved dynamically from project config (do not hard-code `科技主线调研输出/.../代表公司财务估值总表.csv`; use `python -m investment_system.core.project_loader --project <id> --dry-run-paths` to discover the correct path)
- Contract: read `references/contract.md` before changing forecast fields.

## Normalization

- Forecast profit fields use `亿` as the display unit.
- `pe_2026E` and `pe_2027E` should state whether they use current close, target price, or broker source.
- `peg_2026E` must be approximate unless the growth denominator is explicit.
- Always record institution count or source count when available; otherwise label the value as single-source, public-page, user-provided, or judgment.
- Tushare `report_rc` rows are broker forecast source rows, not automatically consensus. Preserve `org_name`, `report_date`, period/quarter, and source count before output generation.
- Tushare `research_report` rows can provide report metadata; they do not replace manual review of the report body when a claim depends on the report text.

## Rules

- Do not blend one broker's aggressive forecast into "consensus" without labeling it.
- If only a single report exists, label it as single-source or first coverage.
- Do not claim Wind/iFind consensus unless the user supplies those data or a verifiable source row.
- Keep forecast date/source close to the field in evidence or source rows.
- Do not blend Tushare rows, public pages, and user-supplied estimates without explicit source labels.
