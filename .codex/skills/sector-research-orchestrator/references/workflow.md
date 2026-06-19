# Workflow

## Standard Run

1. Read `A股科技前两主线调研文件包/02_Codex调研说明手册/Codex调研说明手册.md`.
2. Read the relevant rows in `A股科技前两主线调研文件包/01_调研板块细分方向列表/A股科技前两主线_板块细分方向母表.csv`.
3. Use `investment_system/scripts/research_client.py` as the unified data client.
4. For a known sub-theme, load curated evidence from `investment_system/research/evidence/` when it exists.
5. Run `investment_system/pipelines/run_research.py`; it merges database data with the evidence layer.
6. Run cleanup and validation.
7. If validation fails, fix the pipeline or the evidence input, then rerun validation.

## Output Files

- `科技主线调研输出/00_总表/科技细分方向横向比较表.csv`
- `科技主线调研输出/00_总表/代表公司财务估值总表.csv`
- `科技主线调研输出/00_总表/数据来源索引.csv`
- `科技主线调研输出/01_AI算力硬件/NN_细分方向.md`
- `科技主线调研输出/02_半导体国产替代/NN_细分方向.md`
- `科技主线调研输出/99_日志/缺失数据清单.md`
- `科技主线调研输出/99_日志/冲突数据清单.md`
- `科技主线调研输出/99_日志/调研日志.md`

## Current Known Caveat

`高速光模块` now has a curated evidence file:

```text
investment_system/research/evidence/high_speed_optical_modules.yaml
```

Do not edit final CSV/Markdown as the source of truth. Update the evidence file or the pipeline, then rerun the standard commands.
