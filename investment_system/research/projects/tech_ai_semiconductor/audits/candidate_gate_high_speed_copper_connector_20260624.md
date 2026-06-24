# Candidate Gate - high_speed_copper_connector

- project_id: `tech_ai_semiconductor`
- sector_id: `high_speed_copper_connector`
- run_id: `20260624`
- updated_at: `2026-06-23T17:59:04+00:00`
- candidate_sector_card: `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_candidate_outputs\formal_candidate_high_speed_copper_connector_20260624_sector_card.md`
- metadata: `C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\formal_candidate_outputs\formal_candidate_high_speed_copper_connector_20260624_metadata.json`
- simplified_flow: `Evidence Gate -> Generate Candidate -> Candidate Gate -> Publish Gate -> 人工确认 -> sector-card-only 发布 -> Post-publish Check`
- gate_result: `PASS`
- candidate_status_after_gate: `content_enriched`
- recommend_publish_gate: `False`

## Gate Checks
- sector_card_structure_output_spec: PASS
- source_id_traceability: PASS; rendered=5, known=5
- evidence_id_traceability: PASS; rendered=16, known=16
- nonexistent_source_id: PASS
- missing_evidence_not_deterministic: PASS
- no_investment_action_target_position: PASS
- no_formal_score_or_letter_rating: PASS
- risk_missing_conflict_counter_sections: PASS
- new_industry_evidence_classified: PASS
- validate_outputs: PASS; exit_code=0
- no_gated_formal_generated: PASS
- no_release_manifest_generated: PASS
- no_formal_output_root_write: PASS

## Evidence Strength Classification
- strong: EV-HSCC-PRODUCT-002475-20260624, EV-HSCC-FINSEG-002475-20260624, EV-HSCC-PRODUCT-002130-20260624, EV-HSCC-FINSEG-002130-20260624
- supporting: EV-HSCC-INDUSTRY-CONTEXT-20260624
- context_only: -

## Publish Gate Readiness
- current_candidate_status: `content_enriched`
- recommend_publish_gate: `False`
- reason: Candidate Gate content checks pass, but three companies still lack parsed primary-source industry evidence and named customer/order/certification evidence remains incomplete.

## ERROR/WARNING/INFO 汇总
- ERROR: 0
- WARNING: 0
- INFO: 9

## ERROR
- None

## WARNING
- None

## INFO
- SECTOR_CARD_REQUIRED_SECTIONS_OK
- SOURCE_ID_TRACE_OK: rendered=5, known=5
- EVIDENCE_ID_TRACE_OK: rendered=16, known=16
- MISSING_EVIDENCE_NOT_PROMOTED_TO_CONCLUSION_OK
- NO_FORBIDDEN_INVESTMENT_ACTION_OR_SCORE_OK
- EVIDENCE_STRENGTH_CLASSIFICATION_OK: strong=4, supporting=1, context_only=0
- NO_FORMAL_RATING_OR_SCORE_ENABLED_OK
- VALIDATE_OUTPUTS_OK: exit_code=0
- NO_GATED_FORMAL_CONTENT_IN_CANDIDATE_OK


## validate_outputs excerpt
```text
[PROJECT-AWARE] validate_outputs exit_code=0
[PROJECT-AWARE] Validation is structural-only (passed).
[PROJECT-AWARE] formal_outputs_checked=0
[PROJECT-AWARE] formal_outputs_found=0
```
