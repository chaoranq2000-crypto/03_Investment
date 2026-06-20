# Writer Contract

## Inputs

- Market rows.
- Financial rows.
- Evidence YAML.
- Forecast normalized fields.
- Source rows from local caches and web evidence.

## Outputs

- `科技主线调研输出/00_总表/代表公司财务估值总表.csv`
- `科技主线调研输出/00_总表/科技细分方向横向比较表.csv`
- `科技主线调研输出/00_总表/数据来源索引.csv`
- `科技主线调研输出/01_AI算力硬件/NN_细分方向.md`
- `科技主线调研输出/99_日志/缺失数据清单.md`
- `科技主线调研输出/99_日志/冲突数据清单.md`
- `科技主线调研输出/99_日志/调研日志.md`

## Acceptance

- CSV headers match pipeline constants.
- One sub-theme card exists.
- One comparison row per sub-theme after cleanup.
- Company rows are deduplicated by `(sub_theme, stock_code)`.
- Research-grade reports have company-level depth, required sections, and no debug placeholders outside the data-gap section.
- Research-grade reports cite only source rows that have a local cache path or webpage URL.
