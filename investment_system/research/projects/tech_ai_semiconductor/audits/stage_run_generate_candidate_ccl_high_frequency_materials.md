# Stage Run - generate_candidate

- project_id: `tech_ai_semiconductor`
- sector_id: `ccl_high_frequency_materials`
- stage: `generate_candidate`
- stage_policy_configured: True
- formal_output_write: False
- requires_manual_confirmation: False
- step_count: 1
- blocking_count: 0

## Steps

### build_formal_candidate_outputs
- exit_code: 0
- blocking: False
- command: `C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.build_formal_candidate_outputs --project tech_ai_semiconductor --sector-id ccl_high_frequency_materials --candidate-only --run-id 20260625_m7`
