# Research-Grade Standard

This file carries the current research-grade quality rules.

## Required Sections

A research-grade sector report should include:

1. Conclusion summary: mainline position, realization stage, valuation level, trading heat, and priority.
2. Industry logic: demand source, value change, technology route, and transmission path.
3. Supply-chain position: upstream, midstream, downstream, and cross-theme links.
4. Representative company comparison: exposure, customers/orders, capacity/product stage, financials, valuation, and risks.
5. Financials and valuation: historical revenue/profit, gross margin, PE TTM, PS TTM, 2026E/2027E, PEG or explicit gaps.
6. Market and trading heat: 1/3/6 month return, 20-day turnover, relative strength, and crowding.
7. Catalysts: industry, policy, company, and earnings catalysts.
8. Risks and falsification: valuation, earnings, technology route, competition, and customer introduction.
9. Data sources and gaps: source index, missing evidence, and conflicts.

For the simplified candidate and sector-card-only flow, these sections are quality expectations, not permission to generate total tables, formal source indexes, formal logs, scoring, ratings, target prices, position sizing, or investment advice.

## Source Requirements

Every key claim should point to at least one indexable source:

- local cache under `investment_system/data/raw/...`;
- active evidence under `investment_system/research/evidence/...`;
- stable URL from company, exchange, government, broker, or financial database material.

Source rows or active evidence should preserve:

```text
source_id, source_type, source_name, source_date, source_url or source_file,
related_company, quote_or_excerpt, data_fields_supported, confidence_level
```

Do not accept vague references such as `online material`, `broker reports show`, or `market believes` without a URL, local path, source date, and excerpt.

## Placeholder Ban

Research-grade prose must not contain debug placeholders such as:

- `待核实`
- `调试级`
- `待精确URL`
- `后续补`
- `缺失；待`
- `研报终端核实项`
- `DRAFT_PLACEHOLDER`
- `TODO_MANUAL_EXTRACTION`
- `draft_source_skeleton`
- `EV-DRAFT-`

These concepts may appear only as explicit missing evidence, risks, conflicts, or draft artifacts outside candidate/formal prose.

## Evidence Fallback

When interfaces cannot provide a required field:

- prefer company reports, announcements, exchange records, investor-relations records, and government documents;
- use broker reports or verifiable public forecast pages only with clear source labeling;
- treat media and community discussion as weak context only;
- record unverified items as missing evidence instead of deterministic claims.

## Acceptance

- Pipeline-grade checks cover files, fields, schemas, source IDs, and basic missing data.
- Research-grade checks additionally require readable prose, company-level depth, source traceability, no debug placeholders, and concentrated missing/conflict disclosure.
