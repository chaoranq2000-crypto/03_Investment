# Stage Run - publish_gate

- project_id: `tech_ai_semiconductor`
- sector_id: `high_speed_copper_connector`
- stage: `publish_gate`
- stage_policy_configured: True
- formal_output_write: False
- requires_manual_confirmation: False
- step_count: 2
- blocking_count: 1

## Steps

### prepare_formal_publish
- exit_code: 0
- blocking: False
- command: `C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.prepare_formal_publish --project tech_ai_semiconductor --sector-id high_speed_copper_connector --publish-scope sector_card_only --dry-run --no-overwrite`

### audit_formal_publish_readiness
- exit_code: 1
- blocking: True
- command: `C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.audit_formal_publish_readiness --project tech_ai_semiconductor --sector-id high_speed_copper_connector --publish-scope sector_card_only --release-manifest C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_publish_manifest_high_speed_copper_connector_20260625.json`
