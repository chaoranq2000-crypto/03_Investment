# Stage Run - publish_gate

- project_id: `tech_ai_semiconductor`
- sector_id: `ccl_high_frequency_materials`
- stage: `publish_gate`
- stage_policy_configured: True
- formal_output_write: False
- requires_manual_confirmation: False
- step_count: 2
- blocking_count: 0

## Steps

### prepare_formal_publish
- exit_code: 0
- blocking: False
- command: `C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.prepare_formal_publish --project tech_ai_semiconductor --sector-id ccl_high_frequency_materials --publish-scope sector_card_only --dry-run --no-overwrite`

### audit_formal_publish_readiness
- exit_code: 0
- blocking: False
- command: `C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.audit_formal_publish_readiness --project tech_ai_semiconductor --sector-id ccl_high_frequency_materials --publish-scope sector_card_only --release-manifest C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_publish_manifest_ccl_high_frequency_materials_20260625.json`
