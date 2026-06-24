# Formal Sector Card Directory Integrity - 20260622

- audit_time: 2026-06-23T01:12:50+08:00
- phase_id: 20260622
- project_id: `tech_ai_semiconductor`
- formal_output_root: `C:\Projects\03_Investment\科技主线调研输出`
- conclusion: PASS_WITH_METADATA_WARNING

## 正式 sector card 文件清单

| sector_id | formal sector card | publish log | publish result audit |
| --- | --- | --- | --- |
| `cpo_optical_module_silicon_photonics` | `C:\Projects\03_Investment\科技主线调研输出\3_光通信\高速互连\P0_光模块_CPO_硅光.md` | `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_publish_log_cpo_optical_module_silicon_photonics_20260622.json` | `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_publish_result_audit_cpo_optical_module_silicon_photonics_20260622.md` |
| `optical_chip_components` | `C:\Projects\03_Investment\科技主线调研输出\3_光通信\高速互连\P0_光芯片_激光器_光器件.md` | `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_publish_log_optical_chip_components_20260622.json` | `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_publish_result_audit_optical_chip_components_20260622.md` |

## 正式目录边界

- formal_sector_card_file_count: 2
- expected_sector_cards_present: true
- third_sector_card_present: false
- total_tables_dir_exists: false
- formal_logs_dir_exists: false
- company_table_exists: false
- comparison_table_exists: false
- score_table_exists: false
- source_index_exists: false
- missing_data_log_exists: false
- conflict_data_log_exists: false
- formal_csv_file_count: 0

实际枚举文件：

- `3_光通信\高速互连\P0_光模块_CPO_硅光.md`
- `3_光通信\高速互连\P0_光芯片_激光器_光器件.md`

## 两卡发布链路一致性

| 检查项 | CPO card | optical_chip_components card |
| --- | --- | --- |
| publish log 存在 | PASS | PASS |
| publish result audit 存在 | PASS | PASS |
| publish_scope=`sector_card_only` | PASS | PASS |
| published_files 仅包含 sector_card | PASS | PASS |
| 显式 published_file_count=1 | WARN | PASS |
| 显式 published_file_types=["sector_card"] | WARN | PASS |
| 从 published_files 可推导文件数=1 | PASS | PASS |
| score_status=`score_placeholder_not_applicable` | PASS | PASS |
| no-investment-advice | PASS | PASS |
| source hash = target hash | PASS | PASS |
| 实际 source 文件 hash 与 log 一致 | PASS | PASS |
| 实际 target 文件 hash 与 log 一致 | PASS | PASS |
| overwrite=false | PASS | PASS |
| 未发布总表/日志/score/source index | PASS | PASS |

## 审计命令结果

| command | exit_code | key_result |
| --- | ---: | --- |
| `python -m investment_system.pipelines.sector_research.load_project --project tech_ai_semiconductor --json` | 1 | `errors=[]`, `_load_status=warning`; warning-only, non-blocking |
| `python -m investment_system.pipelines.sector_research.audit_pipeline_readiness --project tech_ai_semiconductor` | 0 | `BLOCKER=0`, `HIGH=0`, `MEDIUM=30`, `LOW=31` |
| `python -m investment_system.pipelines.sector_research.audit_formal_publish_result --project tech_ai_semiconductor --sector-id optical_chip_components` | 0 | `ERROR=0`, `WARNING=0`, `INFO=8`; hash match true |
| `python -m investment_system.pipelines.sector_research.audit_formal_publish_result --project tech_ai_semiconductor --sector-id cpo_optical_module_silicon_photonics` | 1 | `ERROR=2`, `WARNING=0`, `INFO=8`; missing explicit `published_file_count` and `published_file_types` in older CPO publish log |
| `python -m investment_system.pipelines.validate_outputs --project tech_ai_semiconductor` | 0 | structural validation passed; total/log directories still absent |

## ERROR/WARNING/INFO 汇总

- Directory boundary ERROR: 0
- Directory boundary WARNING: 0
- Directory boundary INFO: 2
- Optical publish result audit ERROR: 0
- Optical publish result audit WARNING: 0
- Optical publish result audit INFO: 8
- CPO publish result audit ERROR: 2
- CPO publish result audit WARNING: 0
- CPO publish result audit INFO: 8
- Pipeline readiness BLOCKER: 0
- Pipeline readiness HIGH: 0
- Pipeline readiness MEDIUM: 30
- Pipeline readiness LOW: 31

## 结论

正式输出目录完整性通过：当前仅有两张正式 sector card，且没有总表、正式日志、source index、missing/conflict log、comparison table、score table 或第三张 sector card。

两张卡的实际发布文件、hash、no-overwrite、no-investment-advice、score placeholder 和非 sector 输出不变性均通过。唯一元数据差异是 CPO 的旧 publish log 未包含新字段 `published_file_count` 与 `published_file_types`；从 `published_files` 可推导其实际只发布了 1 个 sector card，但严格按当前审计脚本会产生 2 个 metadata ERROR。

建议可以进入 evidence coverage 扩展计划的准备阶段；在进入下一张正式发布或宣布“两张卡发布链路 schema 完全一致”之前，建议先决定是否补齐旧 CPO publish log 元数据，或让 result audit 对旧日志提供兼容性说明。
