---
name: evidence-miner
description: Mines and structures primary-source evidence for sector research from annual reports, announcements, investor-relations records, exchange Q&A, broker reports, and policy files. Use when filling business exposure, customer/order binding, capacity progress, product stage, catalysts, risks, policy support, or source-index rows.
---

# Evidence Miner

Use this as the fundamental-evidence layer. Store curated evidence as inputs, not as hand-edited final outputs.

## Entry Points

- Evidence directory: `investment_system/research/evidence/`
- Evidence merge code: `investment_system/pipelines/evidence_overrides.py`
- Standard output builder: `investment_system/pipelines/run_research.py`
- Contract: read `references/contract.md` before changing evidence schema.

## Source Priority

1. Company annual/interim/quarterly reports.
2. Company announcements and investor-relations records.
3. Exchange Q&A: 互动易/上证e互动.
4. Government/policy documents.
5. Broker reports and forecast summaries.
6. Media summaries only as weak context, not primary evidence.

## Interface Failure Fallback

When BaoStock, Tencent, AKShare, and Tushare cannot provide a required field, search the web for primary or high-quality secondary evidence. Save the result as structured evidence before it reaches the report:

- Use stable company, exchange, government, broker, or financial-terminal URLs when available.
- Preserve local cache paths for downloaded or extracted documents.
- Record `source_name`, `source_date`, `source_url`, `quote_or_excerpt`, supported fields, and confidence.
- If no verifiable URL or local path exists, write the item to the missing-data log instead of turning it into a report claim.

## Rules

- Each material assertion should map to a source row or evidence note.
- Keep exact source name, date, URL/path, short excerpt, supported fields, confidence.
- Put reusable curated facts in YAML under `investment_system/research/evidence/`.
- Avoid final Markdown/CSV as the source of truth.
- Do not let debug-grade evidence produce final research-grade prose.
