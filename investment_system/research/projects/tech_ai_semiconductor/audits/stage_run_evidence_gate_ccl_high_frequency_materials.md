# Stage Run - evidence_gate

- project_id: `tech_ai_semiconductor`
- sector_id: `ccl_high_frequency_materials`
- stage: `evidence_gate`
- stage_policy_configured: True
- formal_output_write: False
- requires_manual_confirmation: False
- step_count: 3
- blocking_count: 0

## Steps

### audit_evidence_bindings
- exit_code: 0
- blocking: False
- command: `C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.audit_evidence_bindings --project tech_ai_semiconductor`

### audit_evidence_schema
- exit_code: 0
- blocking: False
- command: `C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.audit_evidence_schema --project tech_ai_semiconductor`

### audit_evidence_coverage
- exit_code: 3
- blocking: False
- command: `C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.audit_evidence_coverage --project tech_ai_semiconductor`
