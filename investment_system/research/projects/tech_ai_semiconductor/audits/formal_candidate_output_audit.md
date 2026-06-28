# Formal Candidate Output Audit

- audit_time: 2026-06-27T14:40:43+00:00
- project_id: `tech_ai_semiconductor`
- sector_id: `high_speed_copper_connector`
- output_dir: `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_candidate_outputs`

## 前置门禁结果
- load_project: actual_exit_code=1, warning_count=9, error_count=0, expected_warning_exit_code=3
- readiness: exit_code=0, counts={'BLOCKER': 0, 'HIGH': 0, 'MEDIUM': 30, 'LOW': 31}
- evidence coverage: ok
- P0/P1 coverage counts: {}

## 生成文件清单
- sector_card: `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_candidate_outputs\formal_candidate_high_speed_copper_connector_20260624_sector_card.md`
- metadata: `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_candidate_outputs\formal_candidate_high_speed_copper_connector_20260624_metadata.json`

## Evidence 解析结果
- evidence_file_count: 3
- source_count: 8
- evidence_item_count: 24
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

- `READINESS_GATE_PASSED`: readiness={'BLOCKER': 0, 'HIGH': 0, 'MEDIUM': 30, 'LOW': 31}
- `TARGET_SECTOR_COVERAGE_OK`: high_speed_copper_connector coverage OK.
- `SOURCE_EVIDENCE_CLOSURE_OK`: source_ids=8, evidence_ids=24
- `CANDIDATE_GATE_PASS`: Candidate Gate status=PASS and error_count=0.
- `NO_INVESTMENT_CONCLUSION_OK`: No forbidden buy/sell/add/reduce/build-position wording found.
- `MISSING_EVIDENCE_RETAINED`: Customer/order/certification gaps and Shenyu named AI-server customer gap remain explicit.
- `FORMAL_DIRECTORY_POLLUTION_OK`: No formal_candidate files found in formal output root.
- `VALIDATE_OUTPUTS_OK`: validate_outputs exit_code=0.
