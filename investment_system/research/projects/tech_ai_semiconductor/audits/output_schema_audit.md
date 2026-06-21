# Output Schema Audit - Phase 1E-e-a

Project: `tech_ai_semiconductor`

Scope: engineering output contract audit only. No formal research output is generated.

## Summary

- ERROR: 0
- WARNING: 3
- INFO: 3
- output_type_count: 7
- required_field_count: 85
- deprecated_field_count: 9
- legacy_display_field_count: 23
- hardcoded_output_path_count: 7
- company_table_contract_status: ok
- validate_outputs_contract_status: ok

## Findings

### WARNING

- `THEME_REGISTRY_CSV_PRESENT` (`C:\Projects\03_Investment\investment_system\pipelines\run_research.py`): THEME_REGISTRY_CSV remains in file; audit requires it stay outside project-aware primary path.
- `THEME_REGISTRY_CSV_PRESENT` (`C:\Projects\03_Investment\investment_system\pipelines\validate_outputs.py`): THEME_REGISTRY_CSV remains in file; audit requires it stay outside project-aware primary path.
- `HARDCODED_OUTPUT_PATH_LITERAL` (`C:\Projects\03_Investment\tools\collect_high_speed_optical.py`): found 1 literal occurrence(s) of 科技主线调研输出; verify legacy-only or loader-backed use.

### INFO

- `HARDCODED_OUTPUT_PATH_LITERAL` (`C:\Projects\03_Investment\investment_system\pipelines\run_research.py`): found 2 literal occurrence(s) of 科技主线调研输出; verify legacy-only or loader-backed use.
- `HARDCODED_OUTPUT_PATH_LITERAL` (`C:\Projects\03_Investment\investment_system\pipelines\validate_outputs.py`): found 4 literal occurrence(s) of 科技主线调研输出; verify legacy-only or loader-backed use.
- `NO_FORMAL_OUTPUT_FILES`: No formal output CSV files found; structural contract audit only.
