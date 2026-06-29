---
name: evidence-miner
description: Mines and structures primary-source evidence for sector research from annual reports, announcements, investor-relations records, exchange Q&A, broker reports, and policy files. Use when filling business exposure, customer/order binding, capacity progress, product stage, catalysts, risks, policy support, or source-index rows.
---

# Evidence Miner

Use this as the fundamental-evidence layer. Store curated evidence as inputs, not as hand-edited final outputs.

## Entry Points

- Evidence directory: `investment_system/research/evidence/`
- Source manifest stage: `.codex/skills/evidence-miner/scripts/cli.py collect`
- Draft evidence skeleton stage: `.codex/skills/evidence-miner/scripts/cli.py draft`
- Evidence registration stage: `.codex/skills/evidence-miner/scripts/cli.py register` or `register-apply`
- Curated evidence validator: `.codex/skills/evidence-miner/scripts/cli.py validate-curated`
- Tushare evidence-index fetcher: `.codex/skills/evidence-miner/scripts/cli.py tushare-fetch`
- Tushare evidence-index aliases: `announcements-index`, `research-report-index`, `survey-index`, `irm-qa-index`
- Tushare source manifest alias: `.codex/skills/evidence-miner/scripts/cli.py tushare-source-manifest`
- Tushare cache splitter: `.codex/skills/evidence-miner/scripts/cli.py split-tushare-cache`
- Standard output builder: skill CLIs and `research_writer` candidate flow.
- Contract: read `references/contract.md` before changing evidence schema.

## Evidence Layers

Use three distinct layers. Do not skip directly from raw files to active evidence.

1. Source manifest
   - Built by `evidence_collect`.
   - Lives under `investment_system/data/raw/official_evidence/`.
   - Records raw file paths, text extraction paths, hashes, source dates, URLs when available, source IDs, sidecar lookup keys, and missing metadata fields.
   - Use metadata sidecars to fill CNINFO URL, announcement/source date, company code/name, and title before curation when possible.
   - This is an index of material, not curated evidence.

2. Evidence draft
   - Built by `evidence_draft`.
   - Lives under `investment_system/research/projects/<project_id>/audits/evidence_drafts/`.
   - May contain `status: draft_source_skeleton`, `DRAFT_PLACEHOLDER`, and `TODO_MANUAL_EXTRACTION`.
   - Drafts are blocked from candidate generation and must not be registered as active evidence.

3. Active evidence
   - Lives under `investment_system/research/evidence/`.
   - Created only after manual excerpt, claim, evidence_level, limitation, and missing_fields curation.
   - Validate with `validate_curated_evidence` before or during registration.
   - Registered through `evidence_register`, which updates `run_manifest.yaml` and the sector's `evidence_file_ids[]`.

## Tushare Cache Flow

Use Tushare first for structured evidence indexes such as announcements, broker report metadata, broker forecast rows, institutional surveys, and exchange Q&A when permissions allow it:

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\evidence-miner\scripts\cli.py tushare-fetch --dataset anns_d --code 000001.SZ
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\evidence-miner\scripts\cli.py tushare-fetch --dataset research_report --code 000001.SZ --fetch --write-cache --write-manifest
```

Fetched Tushare rows are raw indexes, not curated evidence. They must become source manifests/drafts before active evidence registration.

For bundled Tushare JSON caches keyed by stock code and dataset, first split them into dataset-level cache files:

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\evidence-miner\scripts\cli.py split-tushare-cache --project tech_ai_semiconductor --sector-id <sector_id> --cache-path investment_system/data/raw/tushare/<cache>.json
```

Add `--write-split --write-manifest` only when writing raw split files and the source manifest is intended. Then feed the generated source manifest into `evidence_draft`; do not register the resulting draft until it has been manually curated.

For new skill-owned Tushare raw-cache envelopes under `investment_system/data/raw/tushare/<dataset>/<date>/`, `split-tushare-cache` can index the envelope directly into a source manifest without rewriting the cache file.

## Source Priority

1. Company annual/interim/quarterly reports.
2. Company announcements and investor-relations records.
3. Exchange Q&A: 互动易/上证e互动.
4. Government/policy documents.
5. Tushare announcement/report/survey/Q&A indexes as discovery aids and source rows.
6. Broker reports and forecast summaries.
7. Media summaries only as weak context, not primary evidence.

## Interface Failure Fallback

When BaoStock, Tencent, AKShare, and Tushare cannot provide a required field, search the web for primary or high-quality secondary evidence. Save the result as structured evidence before it reaches the report:

- Use stable company, exchange, government, broker, or financial-terminal URLs when available.
- Preserve local cache paths for downloaded or extracted documents.
- Record `source_name`, `source_date`, `source_url`, `quote_or_excerpt`, supported fields, and confidence.
- If no verifiable URL or local path exists, write the item to the missing-data log instead of turning it into a report claim.

## Rules

- Each material assertion should map to a source row or evidence note.
- Keep exact source name, date, URL/path, short excerpt, supported fields, confidence.
- Put raw official-source manifests under `investment_system/data/raw/official_evidence/`.
- Put uncurated evidence skeletons under the project audit directory, not under active evidence.
- Put reusable curated facts in YAML under `investment_system/research/evidence/` only after excerpts and claims are reviewed.
- Never register a YAML file that still contains `DRAFT_PLACEHOLDER`, `TODO_MANUAL_EXTRACTION`, or `status: draft_source_skeleton`.
- Treat `validate_curated_evidence` ERROR as a hard stop for `evidence_register`.
- Do not use context-only or unverified secondary material as strong evidence.
- Do not write final sector cards, formal outputs, score tables, or investment advice from this skill.
- Avoid final Markdown/CSV as the source of truth.
- Do not let debug-grade evidence produce final research-grade prose.
