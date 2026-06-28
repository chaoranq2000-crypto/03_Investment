# Stage Run - post_publish_check

- project_id: `tech_ai_semiconductor`
- sector_id: `high_speed_copper_connector`
- stage: `post_publish_check`
- stage_policy_configured: True
- formal_output_write: False
- requires_manual_confirmation: False
- step_count: 3
- blocking_count: 0

## Steps

### audit_formal_publish_result
- exit_code: 0
- blocking: False
- command: `C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.audit_formal_publish_result --project tech_ai_semiconductor --sector-id high_speed_copper_connector`

### validate_outputs
- exit_code: 0
- blocking: False
- command: `C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.validate_outputs --project tech_ai_semiconductor`

### audit_pipeline_readiness
- exit_code: 0
- blocking: False
- command: `C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.audit_pipeline_readiness --project tech_ai_semiconductor`
