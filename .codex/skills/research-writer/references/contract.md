# Writer Contract

## Inputs

- Market rows.
- Financial rows.
- Evidence YAML.
- Forecast normalized fields.
- Source rows from local caches and web evidence.

## Outputs

Paths are resolved dynamically from project config. Use `load_project --project <id> --dry-run-paths` to discover correct paths. Typical resolved structure:

- `<output_root>/00_总表/代表公司财务估值总表.csv`
- `<output_root>/00_总表/科技细分方向横向比较表.csv`
- `<output_root>/00_总表/数据来源索引.csv`
- `<output_root>/<group>_<name>/<priority>_<sector>.md`
- `<output_root>/99_日志/缺失数据清单.md`
- `<output_root>/99_日志/冲突数据清单.md`
- `<output_root>/99_日志/调研日志.md`

## Acceptance

- CSV headers match pipeline constants.
- One sub-theme card exists.
- One comparison row per sub-theme after cleanup.
- Company rows are deduplicated by `(sub_theme, stock_code)`.
- Research-grade reports have company-level depth, required sections, and no debug placeholders outside the data-gap section.
- Research-grade reports cite only source rows that have a local cache path or webpage URL.
