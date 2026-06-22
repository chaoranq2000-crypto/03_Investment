---
name: forecast-normalizer
description: Normalizes institution forecasts for A-share sector research, including 2026E/2027E revenue, net profit, EPS, PE, PEG, forecast source count, report date, and forecast-change notes. Use when broker reports, user-provided forecasts, verifiable public forecast pages, or valuation-forward fields need to be filled or audited; do not assume Wind or iFind access.
---

# Forecast Normalizer

Use this as the forecast and forward-valuation layer.

## Entry Points

- Evidence YAML: `investment_system/research/evidence/`
- Merge code: `investment_system/pipelines/evidence_overrides.py`
- Company table: resolved dynamically from project config (do not hard-code `科技主线调研输出/.../代表公司财务估值总表.csv`; use `load_project --project <id> --dry-run-paths` to discover the correct path)
- Contract: read `references/contract.md` before changing forecast fields.

## Normalization

- Forecast profit fields use `亿` as the display unit.
- `pe_2026E` and `pe_2027E` should state whether they use current close, target price, or broker source.
- `peg_2026E` must be approximate unless the growth denominator is explicit.
- Always record institution count or source count when available; otherwise label the value as single-source, public-page, user-provided, or judgment.

## Rules

- Do not blend one broker's aggressive forecast into "consensus" without labeling it.
- If only a single report exists, label it as single-source or first coverage.
- Do not claim Wind/iFind consensus unless the user supplies those data or a verifiable source row.
- Keep forecast date/source close to the field in evidence or source rows.
