# Quality Gates

Run `investment_system/pipelines/validate_outputs.py --sub-theme <细分方向>` after generation.

Minimum checks:

- Company table has at least 3 companies for the sub-theme.
- Key market fields are not missing: latest price, 1/3/6 month return, 20-day average turnover, PE TTM, PS TTM.
- `数据来源索引.csv` has unique `source_id` values.
- No source excerpt contains stale placeholders such as `缺失元`.
- Markdown card has no unexplained `缺失` placeholder.
- Remaining gaps are listed in `缺失数据清单.md`.
- Any data conflict is listed in `冲突数据清单.md`.

For final investment-facing conclusions:

- Do not treat web search summaries as primary evidence.
- Quote only short excerpts and preserve the source path or URL.
- Separate verified facts, estimates, and judgment.
- Avoid direct buy/sell instructions unless the user explicitly asks for strategy after the evidence base is complete.
