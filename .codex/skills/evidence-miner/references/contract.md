# Evidence Contract

## Inputs

- Theme/sub-theme.
- Company list.
- Available report, announcement, IR, Q&A, policy, and broker-report sources.

## Outputs

- Evidence YAML:
  `investment_system/research/evidence/<theme_slug>.yaml`
- Optional raw documents or extracted snippets under:
  `investment_system/data/raw/evidence/<date>/`
- Source rows compatible with `数据来源索引.csv`.

## Evidence YAML Sections

- `grade`: `draft`, `pipeline`, or `research`.
- `company_overrides`: keyed by stock code.
- `comparison_override`: one row for the cross-theme comparison table.
- `source_rows`: source index rows.
- `logs`: missing/conflict/log markdown content when curated.
- `card_markdown`: optional fully curated card; only use as final research prose when `grade` is `research`.

## Web Evidence Fallback

If interfaces cannot provide a required field, web evidence mining is allowed and expected. The result must be structured as source rows and evidence fields before writing:

- `source_url` must be an http(s) URL or a stable local cache path.
- `quote_or_excerpt` must be short and field-specific.
- `data_fields_supported` must identify which fields the source supports.
- Weak sources should have low confidence and should not be the only support for a high-conviction claim.

## Acceptance

- No important assertion is source-free.
- Evidence differentiates facts, forecasts, and judgment.
- Unverified claims remain in the missing-data log.
- Debug-grade placeholders do not enter final research-grade prose.
