# Stage Run - evidence_draft

- project_id: `tech_ai_semiconductor`
- sector_id: `ccl_high_frequency_materials`
- stage: `evidence_draft`
- stage_policy_configured: True
- formal_output_write: False
- requires_manual_confirmation: False
- step_count: 1
- blocking_count: 0

## Steps

### build_evidence_skeleton
- exit_code: 0
- blocking: False
- command: `C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.build_evidence_skeleton --project tech_ai_semiconductor --sector-id ccl_high_frequency_materials --run-date 2026-06-27 --source-manifest investment_system/data/raw/tushare/cache_splits/tech_ai_semiconductor/ccl_high_frequency_materials/2026-06-27/source_manifest_ccl_high_frequency_materials_tushare_cache_split_2026-06-27.json --evidence-file-id draft_ccl_tushare_split_20260627 --write-draft`
