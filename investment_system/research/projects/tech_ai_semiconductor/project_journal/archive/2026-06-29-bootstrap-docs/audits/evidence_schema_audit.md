# Evidence Schema Audit — Phase 1E-d-b

**Project:** `tech_ai_semiconductor`

**Audit Date:** 2026-06-22

**Phase:** 1E-d-b — Evidence schema / source_id 规范化

**Scope:** Engineering schema/source_id audit only. This report is not an investment report.

---

## 1. Summary

| Metric | Value |
|---|---|
| ERROR | 0 |
| WARNING | 0 |
| INFO | 10 |
| evidence_file_count | 8 |
| source_count | 61 |
| evidence_item_count | 64 |
| missing_source_metadata_count | 0 |
| duplicate_source_count | 0 |
| orphan_source_count | 0 |
| unused_source_count | 10 |
| source_type_errors | 0 |
| access_method_errors | 0 |
| missing_location_errors | 0 |
| migration_field_count | 0 |
| canonical_sector_binding_count | 9 |

---

## 2. Evidence Files

| evidence_file_id | sources | items | missing_metadata | duplicates | orphans | unused | migration_fields |
|---|---|---:|---:|---:|---:|---:|---:|---|
| high_speed_optical_modules | 22 | 9 | 0 | 0 | 0 | 5 | - |
| trading_heat_optical_chain | 1 | 12 | 0 | 0 | 0 | 0 | - |
| optical_components_fau_precision_optics | 18 | 7 | 0 | 0 | 0 | 5 | - |
| high_speed_copper_connector | 2 | 6 | 0 | 0 | 0 | 0 | - |
| trading_heat_high_speed_copper_connector | 1 | 5 | 0 | 0 | 0 | 0 | - |
| high_speed_copper_connector_product_validation | 5 | 13 | 0 | 0 | 0 | 0 | - |
| ai_server_pcb_high_speed_board | 6 | 6 | 0 | 0 | 0 | 0 | - |
| ccl_high_frequency_materials | 6 | 6 | 0 | 0 | 0 | 0 | - |

---

## 3. Findings

### INFO (10)

- `UNUSED_SOURCE` (`investment_system/research/evidence/high_speed_optical_modules.yaml`): source_id 'AKSHARE-ERR-001-20260619' is defined but never referenced by any evidence_item.
- `UNUSED_SOURCE` (`investment_system/research/evidence/high_speed_optical_modules.yaml`): source_id 'BAO-DAILY-HSOM-20260619' is defined but never referenced by any evidence_item.
- `UNUSED_SOURCE` (`investment_system/research/evidence/high_speed_optical_modules.yaml`): source_id 'BAO-PROFIT-HSOM-20260619' is defined but never referenced by any evidence_item.
- `UNUSED_SOURCE` (`investment_system/research/evidence/high_speed_optical_modules.yaml`): source_id 'OCFP-CNINFO-SHARED-20260619' is defined but never referenced by any evidence_item.
- `UNUSED_SOURCE` (`investment_system/research/evidence/high_speed_optical_modules.yaml`): source_id 'TENCENT-DAILY-HSOM-20260619' is defined but never referenced by any evidence_item.
- `UNUSED_SOURCE` (`investment_system/research/evidence/optical_components_fau_precision_optics.yaml`): source_id 'AKSHARE-FIN-OCFP-20260620' is defined but never referenced by any evidence_item.
- `UNUSED_SOURCE` (`investment_system/research/evidence/optical_components_fau_precision_optics.yaml`): source_id 'BAO-DAILY-OCFP-20260620' is defined but never referenced by any evidence_item.
- `UNUSED_SOURCE` (`investment_system/research/evidence/optical_components_fau_precision_optics.yaml`): source_id 'BAO-PROFIT-OCFP-20260620' is defined but never referenced by any evidence_item.
- `UNUSED_SOURCE` (`investment_system/research/evidence/optical_components_fau_precision_optics.yaml`): source_id 'EVIDENCE-YAML-OCFP-20260620' is defined but never referenced by any evidence_item.
- `UNUSED_SOURCE` (`investment_system/research/evidence/optical_components_fau_precision_optics.yaml`): source_id 'HSOM-CROSS-REF-20260619' is defined but never referenced by any evidence_item.

---

## 4. Source ID Naming Rules

```
{PROVIDER}-{SCOPE_TYPE}-{SCOPE_ID}-{DATE}
```

Examples:
- `BAO-DAILY-HSOM-20260619` — BaoStock market data for high-speed optical modules, collected 2026-06-19
- `BAO-STOCK-300308-20260619` — BaoStock financial data for stock 300308, collected 2026-06-19
- `CNINFO-AR-300394-20260407` — CNINFO annual report for 300394, report date 2026-04-07
- `HSOM-BUNDLE-300308-20260619` — Legacy evidence bundle migrated from high_speed_optical_modules.yaml

| Field | Description |
|---|---|
| PROVIER | BAO, TENCENT, AKSHARE, CNINFO, CURATED, LEGACY, EVIDENCE |
| SCOPE_TYPE | DAILY, PROFIT, STOCK, SECTOR, COMPARISON, BUNDLE, AR |
| SCOPE_ID | Stock code, sector_id, or scope identifier |
| DATE | YYYYMMDD collection or report date |

---

## 5. Source Metadata Minimum Standard

Each source in `source_index[]` must have:

| Field | Required | Notes |
|---|:---:|---|
| source_id | Yes | Unique within file |
| title | Yes | Descriptive name |
| source_type | Yes | Legal values defined in schema |
| date | Yes | YYYY-MM-DD format |
| publisher | Yes | Data provider name |
| access_method | Yes | Legal values defined in schema |
| url | No* | Required if web-downloadable |
| local_path | No* | Required if local cache |
| dataset_ref | No* | Required if dataset reference |
| reliability_level | No | 高/中高/中/中低/低 |
| notes | No | Additional context |

*At least one of url/local_path/dataset_ref must be present.

---

## 6. Source Type Legal Values

| Value | Description |
|---|---|
| market_data | BaoStock/Tencent/AKShare market price data |
| financial_data | BaoStock/Tencent/AKShare financial statement data |
| annual_report | CNINFO/company annual report PDF |
| broker_report | Securities firm research report |
| news | News article |
| regulatory_filing | Exchange/regulator filing |
| curated_evidence | Manually curated evidence bundle |
| historical_migrated | Migrated from historical YAML |
| self_reference | Reference to this evidence YAML itself |
| cross_reference | Reference to another evidence YAML |
| database | BaoStock/Tencent/AKShare query result |
| diagnostic_error | Error/diagnostic record |
| diagnostic_disabled | Disabled historical source |

---

## 7. Duplicate Source ID Resolution

### high_speed_optical_modules.yaml

| Original IDs (merged) | Resolved To | Reason |
|---|---|---|
| SRC-BAO-300308-20260619185911/190729/191111 | BAO-STOCK-300308-20260619 | Same data, different query times |
| SRC-BAO-300502-20260619185911/190729/191111 | BAO-STOCK-300502-20260619 | Same data, different query times |
| SRC-BAO-300394-20260619185911/190729/191111 | BAO-STOCK-300394-20260619 | Same data, different query times |
| SRC-BAO-603083-20260619185911/190729/191111 | BAO-STOCK-603083-20260619 | Same data, different query times |
| SRC-BAO-002281-20260619185911/190729/191111 | BAO-STOCK-002281-20260619 | Same data, different query times |
| SRC-BAO-000988-20260619185911/190729/191111 | BAO-STOCK-000988-20260619 | Same data, different query times |
| SRC-BAO-300570-20260619185911/190729/191111 | BAO-STOCK-300570-20260619 | Same data, different query times |
| SRC-BAO-300548-20260619185911/190729/191111 | BAO-STOCK-300548-20260619 | Same data, different query times |

### optical_components_fau_precision_optics.yaml

No duplicate source_ids detected.

---

## 8. Cross-File Reference Notes

### Companies appearing in both evidence files:

| Company | high_speed_optical_modules | optical_components_fau_precision_optics |
|---|---|---|
| 天孚通信 (300394) | Yes | Yes |
| 太辰光 (300570) | Yes | Yes |

Resolution: Each file retains its own source_id. A `cross_reference` type source entry documents the relationship. CNINFO annual report authority remains in optical_components_fau_precision_optics.yaml.

---

## 9. URL/local_path/dataset_ref Coverage

| Evidence File | Sources | Has Location | Missing Location |
|---|---|---:|---:|---:|
| high_speed_optical_modules | 22 | 22 | 0 |
| trading_heat_optical_chain | 1 | 1 | 0 |
| optical_components_fau_precision_optics | 18 | 18 | 0 |
| high_speed_copper_connector | 2 | 2 | 0 |
| trading_heat_high_speed_copper_connector | 1 | 1 | 0 |
| high_speed_copper_connector_product_validation | 5 | 5 | 0 |
| ai_server_pcb_high_speed_board | 6 | 6 | 0 |
| ccl_high_frequency_materials | 6 | 6 | 0 |

Note: BaoStock/Tencent/AKShare database sources intentionally lack web URLs. local_path is sufficient for audit trail.

---

## 10. Recommendation

- **ERROR: 0**

- **WARNING: 0**

- **INFO: 10**

Evidence schema/source_id normalization status:
- ERROR=0: Canonical schema/source_id structure is valid.

**Recommended next stage: 1E-e (output fields vs output_spec/schema alignment).**

Rationale:
- Canonical evidence schema/source_id is now in place.
- Source metadata minimum standard is documented.
- Source_id naming rules are standardized.
- Duplicate source_ids are resolved.
- Cross-file references are documented.
- ERROR=0 confirms schema readiness for output generation.