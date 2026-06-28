# Stage Run - scope_check

- project_id: `tech_ai_semiconductor`
- sector_id: `high_speed_copper_connector`
- stage: `scope_check`
- stage_policy_configured: True
- formal_output_write: False
- requires_manual_confirmation: False
- step_count: 3
- blocking_count: 0

## Steps

### load_project
- exit_code: 3
- blocking: False
- command: `C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.load_project --project tech_ai_semiconductor --json`

### audit_pipeline_readiness
- exit_code: 0
- blocking: False
- command: `C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.audit_pipeline_readiness --project tech_ai_semiconductor`

### validate_outputs
- exit_code: 0
- blocking: False
- command: `C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.validate_outputs --project tech_ai_semiconductor`
