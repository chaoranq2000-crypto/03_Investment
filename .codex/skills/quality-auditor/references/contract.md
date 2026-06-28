# Audit Contract

## Inputs

- Final output CSVs and Markdown cards.
- Raw data partitions.
- Evidence YAML.
- Data-source diagnostics.

## Checks

- Required files exist.
- Company rows >= expected minimum.
- Required market and valuation fields are complete.
- `source_date`, `source_url`, `confidence_level`, and `data_source` are semantically valid.
- `source_id` values are unique.
- No invalid source excerpts such as `缺失元`.
- One comparison row per sub-theme.
- Card has no unexplained `缺失`.
- Research-grade card has required sections and company-level discussion.
- Research-grade card has no debug placeholders outside the data-gap section.
- Source rows have `source_url` values that are local cache paths, evidence paths, or http(s) URLs.
- Tushare-sourced rows preserve provider identity and never expose `TUSHARE_TOKEN`.
- Forecast rows do not imply Wind/iFind access unless user-supplied data is cited.
- Candidate and formal cards do not contain `DRAFT_PLACEHOLDER`, `TODO_MANUAL_EXTRACTION`, `draft_source_skeleton`, or `EV-DRAFT-`.
- Candidate and formal cards do not contain investment advice, target price, position sizing, A/B/C/D/E ratings, or formal scoring unless an explicit separate scoring process is in scope.

## Acceptance

- `quality-auditor validate-outputs --project <project_id> --sector-id <sector_id> --grade pipeline` exits 0.
- `quality-auditor validate-outputs --project <project_id> --sector-id <sector_id> --grade research` exits 0 for final reports.
- Remaining data gaps are explicitly listed.
- Data-source failures are described without overclaiming root cause.
- For the simplified sector-card-only flow, `candidate_gate`, `publish_gate`, and `post_publish_check` are the preferred gate entry points.
