# Formal Candidate Output Audit

- audit_time: 2026-06-28T14:18:18+00:00
- project_id: `tech_ai_semiconductor`
- sector_id: `ai_server_pcb_high_speed_board`
- output_dir: `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_candidate_outputs`

## 前置门禁结果
- load_project: actual_exit_code=1, warning_count=9, error_count=0, expected_warning_exit_code=3
- readiness: exit_code=0, counts={'BLOCKER': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 26}
- evidence coverage: ok
- P0/P1 coverage counts: {}

## 生成文件清单
- sector_card: `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_candidate_outputs\formal_candidate_ai_server_pcb_high_speed_board_20260628_sector_card.md`
- metadata: `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_candidate_outputs\formal_candidate_ai_server_pcb_high_speed_board_20260628_metadata.json`

## Evidence 解析结果
- evidence_file_count: 1
- source_count: 6
- evidence_item_count: 6
- source_id_closure: True
- evidence_id_closure: True

## 质量门禁结果
- no_investment_conclusion: True
- formal_directory_pollution: True
- output_spec_schema_alignment: shape_errors=0, shape_warnings=0
- missing_conflict_logs: failed

## ERROR/WARNING/INFO 汇总
- ERROR: 0
- WARNING: 1
- INFO: 8
- recommend_next_stage: True

## Findings

### WARNING

- `LOAD_PROJECT_WARNING_ONLY`: load_project warning-only count=9; expected exit code=3

### INFO

- `READINESS_GATE_PASSED`: readiness={'BLOCKER': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 26}
- `TARGET_SECTOR_COVERAGE_OK`: ai_server_pcb_high_speed_board coverage OK.
- `SOURCE_EVIDENCE_CLOSURE_OK`: source_ids=6, evidence_ids=6
- `CANDIDATE_GATE_PASS`: Candidate Gate status=PASS and error_count=0.
- `NO_INVESTMENT_CONCLUSION_OK`: No forbidden buy/sell/add/reduce/build-position wording found.
- `MISSING_EVIDENCE_SECTION_PRESENT`: Generic missing/counter-evidence markers are present.
- `FORMAL_DIRECTORY_POLLUTION_OK`: No formal_candidate files found in formal output root.
- `VALIDATE_OUTPUTS_OK`: validate_outputs exit_code=0.
