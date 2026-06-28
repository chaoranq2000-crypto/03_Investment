# Formal Publish Result Audit

- audit_time: 2026-06-25T07:34:45+00:00
- project_id: `tech_ai_semiconductor`
- sector_id: `high_speed_copper_connector`
- publish_scope: `sector_card_only`
- source_stage: `formal_candidate`
- publish_log: `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_publish_log_high_speed_copper_connector_20260624.json`
- release_manifest: `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_publish_manifest_high_speed_copper_connector_20260624.json`
- 发布源文件: `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_candidate_outputs\formal_candidate_high_speed_copper_connector_20260624_sector_card.md`
- source_candidate_file: `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_candidate_outputs\formal_candidate_high_speed_copper_connector_20260624_sector_card.md`
- 发布目标文件: `C:\Projects\03_Investment\科技主线调研输出\3_光通信\高速互连\P1_高速铜缆_DAC_AEC_连接器.md`
- source_hash: `355c703e8e60098a7d366ce28494f983a570474c67dde99e051e4b0acd901f91`
- target_hash: `355c703e8e60098a7d366ce28494f983a570474c67dde99e051e4b0acd901f91`
- source_target_hash_match: True
- overwrite: False
- sector_card_only: True
- published_file_count: 1
- published_file_types: ['sector_card']
- formal_markdown_file_count: 3
- total_tables_dir_exists: False
- logs_dir_exists: False
- non_sector_outputs_unchanged: True
- no_investment_conclusion: True
- score_placeholder_not_applicable: True
- validate_outputs_exit_code: 0

## ERROR/WARNING/INFO 汇总
- ERROR: 0
- WARNING: 0
- INFO: 10
- recommend_next_stage: True

## Findings

### INFO

- `PUBLISH_LOG_PRESENT` (`C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_publish_log_high_speed_copper_connector_20260624.json`): publish log exists.
- `SECTOR_CARD_ONLY_PUBLISHED`: published_files contains only sector_card.
- `TARGET_PATH_MATCHES_MANIFEST`: formal sector card path equals release manifest target.
- `SOURCE_TARGET_HASH_OK`: source hash equals target hash.
- `NON_SECTOR_OUTPUTS_UNCHANGED`: shared tables/logs/score targets unchanged.
- `NO_INVESTMENT_CONCLUSION_OK`: No forbidden investment wording found in published sector card.
- `FORMAL_SECTOR_CARD_COUNT_OK`: formal output root contains exactly 3 markdown sector cards.
- `TOTAL_TABLES_DIR_ABSENT`: 00_总表 directory is absent.
- `LOGS_DIR_ABSENT`: 99_日志 directory is absent.
- `VALIDATE_OUTPUTS_OK`: validate_outputs exit_code=0.
