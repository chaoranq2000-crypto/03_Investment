# Quality Gates

For the simplified sector-card-only workflow, run gates through skill CLIs:

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\quality-auditor\scripts\cli.py evidence-gate --project tech_ai_semiconductor --sector-id <sector_id>
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\quality-auditor\scripts\cli.py candidate-gate --project tech_ai_semiconductor --sector-id <sector_id>
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" .codex\skills\sector-research-orchestrator\scripts\cli.py publish-gate --project tech_ai_semiconductor --sector-id <sector_id> --publish-scope sector_card_only
```

Use `quality-auditor validate-outputs --grade pipeline/research` only when debugging the underlying output contract.

Evidence Gate checks:

- Evidence files are registered in `run_manifest.yaml`.
- Sector bindings use canonical `sector_id` and `evidence_file_ids[]`.
- Active evidence YAML passes schema validation.
- Target sector coverage is OK.
- Unrelated P0/P1 MISSING sectors may be warning-only only when `workflow_stages.yaml` explicitly encodes that rule.

Candidate Gate checks:

- Candidate files stay under `investment_system/research/projects/<project_id>/audits/formal_candidate_outputs/`.
- `source_id` and `evidence_id` references close against active evidence.
- Missing evidence is retained as missing/risk/counter-evidence and is not converted into a deterministic claim.
- `DRAFT_PLACEHOLDER`, `TODO_MANUAL_EXTRACTION`, `draft_source_skeleton`, and `EV-DRAFT-` references are blocking failures.
- Buy/sell/build/add/reduce/clear-position wording, target price, position sizing, formal scoring, and A/B/C/D/E ratings are blocking failures.
- `risk`, `missing`, `conflict / counter-evidence`, `NOT_RATED`, and `NOT_INVESTMENT_ADVICE` markers are present.

Publish Gate checks:

- The stage is dry-run only.
- `publish_scope` is `sector_card_only`.
- The source candidate file path and hash are recorded.
- The target formal path is project-aware and no-overwrite is enforced.
- `file_map` contains only `sector_card`.
- Total tables, formal logs, source index, missing/conflict log, comparison table, score table, and release manifest are excluded/no-action.

Post-publish Check verifies:

- Source hash equals target hash.
- The formal directory card count matches expectation.
- No total table, formal log, source index, missing/conflict log, comparison table, score table, formal scoring, or investment advice was created by the publish stage.
- Publish log exists and records `sector_card_only`.
- `validate_outputs` and readiness pass.

Pipeline-grade checks:

- Company table has at least 3 companies for the sub-theme.
- Key market fields are not missing: latest price, 1/3/6 month return, 20-day average turnover, PE TTM, PS TTM.
- `数据来源索引.csv` has unique `source_id` values.
- No source excerpt contains stale placeholders such as `缺失元`.
- Markdown card has no unexplained `缺失` placeholder.
- Remaining gaps are listed in `缺失数据清单.md`.
- Any data conflict is listed in `冲突数据清单.md`.
- For sector-card-only phases, candidate artifacts must stay under `investment_system/research/projects/<project_id>/audits/`, and formal output writes are forbidden until `publish_sector_card_only` has explicit user confirmation.

Research-grade checks:

- Markdown has the required report sections: conclusion summary, industry logic, supply-chain position, representative company comparison, financial/valuation discussion, market/trading heat, catalysts, risk/falsification, and data sources/gaps.
- Each representative company has a company-specific discussion, not only a table row.
- Main prose has no debug placeholders such as `待核实`, `调试级`, `待精确URL`, or `后续补`.
- Source rows have a verifiable local cache path or webpage URL.
- Interface failures are either repaired through web evidence mining or concentrated in the data-gap section.
- Draft skeleton markers such as `DRAFT_PLACEHOLDER` and `TODO_MANUAL_EXTRACTION` must not appear in candidate or formal outputs.
- For full research-grade review details, use `quality-auditor/references/research_grade_standard.md`.

For final investment-facing conclusions:

- Do not treat web search summaries as primary evidence.
- Quote only short excerpts and preserve the source path or URL.
- Separate verified facts, estimates, and judgment.
- Avoid direct buy/sell instructions unless the user explicitly asks for strategy after the evidence base is complete.

For the current project, do not treat `audit_evidence_coverage` nonzero exit as automatically blocking when the target sector is OK and unrelated P0/P1 sectors remain MISSING. This warning-only rule is encoded in `workflow_stages.yaml`.
