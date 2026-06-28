# Formal Publish Readiness Audit

- audit_time: 2026-06-28T14:16:20+00:00
- project_id: `tech_ai_semiconductor`
- sector_id: `ai_server_pcb_high_speed_board`
- gated formal source: `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\gated_formal_outputs`
- formal candidate source: `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_candidate_outputs`
- release manifest: `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_publish_manifest_ai_server_pcb_high_speed_board_20260628.json`
- publish_scope: `sector_card_only`
- source_stage: `gated_formal`
- dry_run: True
- manual_confirmation_required: True
- confirm_publish_requested: False
- publish_executed: False

## 最终正式发布目标路径清单
- sector_card: `C:\Projects\03_Investment\科技主线调研输出\4_PCB\CCL\载板\P1_AI服务器PCB_高速通信板.md`

## 明确排除的正式输出动作
- company_table: publish_action=False; target=`C:\Projects\03_Investment\科技主线调研输出\00_总表\代表公司财务估值总表.csv`
- sector_comparison_table: publish_action=False; target=`C:\Projects\03_Investment\科技主线调研输出\00_总表\科技细分方向横向比较表.csv`
- source_index: publish_action=False; target=`C:\Projects\03_Investment\科技主线调研输出\00_总表\数据来源索引.csv`
- missing_data_log: publish_action=False; target=`C:\Projects\03_Investment\科技主线调研输出\99_日志\缺失数据清单.md`
- conflict_data_log: publish_action=False; target=`C:\Projects\03_Investment\科技主线调研输出\99_日志\冲突数据清单.md`
- score_table: publish_action=False; target=`C:\Projects\03_Investment\科技主线调研输出\00_总表\科技细分方向横向比较表.csv`
- release_manifest: publish_action=False; target=`C:\Projects\03_Investment\科技主线调研输出\99_日志\formal_publish_manifest_ai_server_pcb_high_speed_board_20260628.json`

## 门禁结果
- source_id_closure: True
- evidence_id_closure: True
- no_investment_conclusion: True
- score_placeholder_not_applicable: True
- target_overwrite_risk: False
- formal_directory_pollution: True
- validate_outputs_exit_code: 0

## ERROR/WARNING/INFO 汇总
- ERROR: 0
- WARNING: 0
- INFO: 8
- recommend_next_stage: True

## Findings

### INFO

- `RELEASE_MANIFEST_PRESENT` (`C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_publish_manifest_ai_server_pcb_high_speed_board_20260628.json`): release manifest exists.
- `FINAL_TARGET_PATHS_RESOLVED`: target_count=1
- `SOURCE_HASH_SIZE_OK`: verified 1 source files.
- `SECTOR_CARD_ONLY_SCOPE_OK`: Only sector_card is mapped for potential publish; other outputs are excluded/no-action.
- `VALIDATE_OUTPUTS_OK`: validate_outputs exit_code=0.
- `NO_INVESTMENT_CONCLUSION_OK`: No forbidden investment wording found in gated files.
- `SCORE_PLACEHOLDER_OK`: score remains placeholder/not_applicable.
- `FORMAL_DIRECTORY_POLLUTION_OK`: No final output write detected by gated audit.
