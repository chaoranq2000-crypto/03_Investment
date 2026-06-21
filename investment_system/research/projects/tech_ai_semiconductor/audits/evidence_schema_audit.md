# Evidence Schema Audit - Phase 1E-d-b

Project: `tech_ai_semiconductor`

Scope: engineering schema/source_id audit only. This report is not an investment report.

## Summary

- ERROR: 0
- WARNING: 1
- INFO: 2
- evidence_file_count: 2
- source_count: 48
- evidence_item_count: 16
- missing_source_metadata_count: 1
- legacy_only_field_count: 16
- canonical_sector_binding_count: 2

## Evidence Files

| evidence_file_id | canonical_sector_ids | sources | evidence_items | missing_source_metadata | legacy_fields |
|---|---|---:|---:|---:|---|
| high_speed_optical_modules | cpo_optical_module_silicon_photonics | 31 | 9 | 1 | card_markdown, company_overrides, comparison_override, description, grade, logs, source_rows, sub_theme |
| optical_components_fau_precision_optics | optical_chip_components | 17 | 7 | 0 | card_markdown, company_overrides, comparison_override, description, grade, logs, source_rows, sub_theme |

## Findings

### WARNING

- `MISSING_SOURCE_METADATA` (`investment_system/research/evidence/high_speed_optical_modules.yaml`): source_id 'SRC-LEGACY-DISABLED-001' lacks title/date or url/path metadata.

### INFO

- `LEGACY_FIELDS_RETAINED` (`investment_system/research/evidence/high_speed_optical_modules.yaml`): legacy top-level fields retained for compatibility: card_markdown, company_overrides, comparison_override, description, grade, logs, source_rows, sub_theme
- `LEGACY_FIELDS_RETAINED` (`investment_system/research/evidence/optical_components_fau_precision_optics.yaml`): legacy top-level fields retained for compatibility: card_markdown, company_overrides, comparison_override, description, grade, logs, source_rows, sub_theme

## Recommendation

Evidence schema/source_id normalization has a usable canonical wrapper when ERROR=0. Warnings about missing source metadata should be resolved before treating migrated legacy evidence as research-grade.
