# Formal Candidate Output Audit

- audit_time: 2026-06-21T18:15:44+00:00
- project_id: `tech_ai_semiconductor`
- sector_id: `cpo_optical_module_silicon_photonics`
- output_dir: `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_candidate_outputs`

## 前置门禁结果
- load_project: actual_exit_code=3, warning_count=7, error_count=0, expected_warning_exit_code=3
- readiness: exit_code=0, counts={'BLOCKER': 0, 'HIGH': 0, 'MEDIUM': 30, 'LOW': 31}
- evidence coverage: ok
- P0/P1 coverage counts: {'ok': 2, 'partial': 0, 'missing': 15}

## 生成文件清单
- sector_card: `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_candidate_outputs\formal_candidate_cpo_optical_module_silicon_photonics_20260622_sector_card.md`
- company_table: `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_candidate_outputs\formal_candidate_cpo_optical_module_silicon_photonics_20260622_company_table.csv`
- sector_comparison_table: `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_candidate_outputs\formal_candidate_cpo_optical_module_silicon_photonics_20260622_sector_comparison_table.csv`
- source_index: `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_candidate_outputs\formal_candidate_cpo_optical_module_silicon_photonics_20260622_source_index.csv`
- missing_data_log: `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_candidate_outputs\formal_candidate_cpo_optical_module_silicon_photonics_20260622_missing_data_log.csv`
- conflict_data_log: `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_candidate_outputs\formal_candidate_cpo_optical_module_silicon_photonics_20260622_conflict_data_log.csv`
- score_table: `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_candidate_outputs\formal_candidate_cpo_optical_module_silicon_photonics_20260622_score_table.csv`
- metadata: `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_candidate_outputs\formal_candidate_cpo_optical_module_silicon_photonics_20260622_metadata.json`

## Evidence 解析结果
- evidence_file_count: 2
- source_count: 24
- evidence_item_count: 15
- source_id_closure: True
- evidence_id_closure: True

## 质量门禁结果
- no_investment_conclusion: True
- formal_directory_pollution: True
- output_spec_schema_alignment: shape_errors=0, shape_warnings=8
- missing_conflict_logs: ok

## ERROR/WARNING/INFO 汇总
- ERROR: 0
- WARNING: 1
- INFO: 9
- recommend_next_stage: True

## Findings

### WARNING

- `LOAD_PROJECT_WARNING_ONLY`: load_project warning-only count=7; expected exit code=3

### INFO

- `READINESS_GATE_PASSED`: readiness={'BLOCKER': 0, 'HIGH': 0, 'MEDIUM': 30, 'LOW': 31}
- `TARGET_SECTOR_COVERAGE_OK`: cpo_optical_module_silicon_photonics coverage OK.
- `OUTPUT_CONTRACT_SHAPE_OK`: shape_warnings=8
- `EVIDENCE_FILES_RESOLVED`: files=2, sources=24, evidence_items=15
- `SOURCE_EVIDENCE_CLOSURE_OK`: source_ids=18, evidence_ids=15
- `MISSING_DATA_LOG_PRESENT` (`C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_candidate_outputs\formal_candidate_cpo_optical_module_silicon_photonics_20260622_missing_data_log.csv`): missing_data_log exists with rows.
- `CONFLICT_DATA_LOG_PRESENT` (`C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_candidate_outputs\formal_candidate_cpo_optical_module_silicon_photonics_20260622_conflict_data_log.csv`): conflict_data_log exists with rows.
- `FORMAL_DIRECTORY_POLLUTION_OK`: No formal_candidate files found in formal output root.
- `NO_INVESTMENT_CONCLUSION_OK`: No forbidden buy/sell/add/reduce/build-position wording found.
