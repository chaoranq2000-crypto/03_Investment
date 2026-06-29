# Evidence Binding Audit — Phase 1E-d-a (Refreshed)

**Project:** `tech_ai_semiconductor`  
**Audit Date:** 2026-06-22  
**Phase:** 1E-d-a — Evidence 绑定迁移到 canonical sector_id + Evidence 审计入口  
**Scope:** Engineering audit only. This report records evidence binding metadata and resolver behavior. It is not an investment report, does not score sectors, and does not treat old evidence YAML files as research-grade outputs.

---

## 1. Baseline

### 1.1 Evidence Registry Architecture

| Layer | Role | Status |
|---|---|---|
| `run_manifest.yaml` `evidence_files[]` | Project-aware evidence registry | ✅ Correct |
| `sector_universe.yaml` `evidence_file_ids[]` | Per-sector evidence binding | ✅ Correct |
| `load_project.py` `resolve_evidence_files_for_sector()` | Project-aware resolver | ✅ Working |
| `evidence_overrides.py` `THEME_EVIDENCE_FILES` | Legacy-only adapter | ✅ Marked `LEGACY_ONLY_EVIDENCE_REGISTRY = True` |

### 1.2 Loader Validation Baseline

| Metric | Value |
|---|---|
| `errors` | 0 |
| `evidence_file_count` | 2 |
| `seed_document_count` | 1 |
| `retired_legacy_output_count` | 8 |
| Existing warnings | 6 (all P2/P3 sector thin/missing coverage, expected) |

---

## 2. Evidence Files

| evidence_file_id | canonical sector_id | legacy_sector_id | path | status | action | exists |
|---|---|---|---|---|---|---|
| `high_speed_optical_modules` | `cpo_optical_module_silicon_photonics` | `cpo_optical_module` | `investment_system/research/evidence/high_speed_optical_modules.yaml` | `indexed_existing_evidence` | `index_only` | ✅ yes |
| `optical_components_fau_precision_optics` | `optical_chip_components` | `optical_components` | `investment_system/research/evidence/optical_components_fau_precision_optics.yaml` | `indexed_existing_evidence` | `index_only` | ✅ yes |

---

## 3. Canonical Binding Verification

### 3.1 Canonical Sector ID Resolution

```
Input: cpo_optical_module_silicon_photonics
  → ef_id=high_speed_optical_modules
  → path=investment_system/research/evidence/high_speed_optical_modules.yaml
  → match_type=evidence_file_id
  → exists=True

Input: optical_chip_components
  → ef_id=optical_components_fau_precision_optics
  → path=investment_system/research/evidence/optical_components_fau_precision_optics.yaml
  → match_type=evidence_file_id
  → exists=True
```

### 3.2 Legacy Alias Resolution

| Legacy Input | Resolved Evidence | Canonical Sector |
|---|---|---|
| `high_speed_optical_modules` (evidence_file_id) | `high_speed_optical_modules` | `cpo_optical_module_silicon_photonics` |
| `optical_components_fau_precision_optics` (evidence_file_id) | `optical_components_fau_precision_optics` | `optical_chip_components` |
| `cpo_optical_module` (legacy_sector_id) | `high_speed_optical_modules` | `cpo_optical_module_silicon_photonics` |
| `optical_components` (legacy_sector_id) | `optical_components_fau_precision_optics` | `optical_chip_components` |

✅ All legacy aliases resolve to the same canonical result.

### 3.3 `sector_universe.yaml` Binding Check

| Sector | `evidence_file_ids` | Bound Evidence File |
|---|---|---|
| `cpo_optical_module_silicon_photonics` | `["high_speed_optical_modules"]` | ✅ |
| `optical_chip_components` | `["optical_components_fau_precision_optics"]` | ✅ |

Both sectors correctly reference their evidence files via `evidence_file_ids[]`.

---

## 4. Sector Evidence Coverage

| Status | Sectors |
|---|---|
| ✅ **ok** (evidence bound) | `cpo_optical_module_silicon_photonics`, `optical_chip_components` |
| ⚠️ **P0/P1 missing** (expected in this phase) | 15 P0/P1 sectors without bound evidence YAML |
| ℹ️ **P2/P3 missing** (expected) | 12 P2/P3 sectors without bound evidence YAML |

### P0/P1 Sectors Without Bound Evidence (Expected — Phase 1E-d-a only establishes binding; does not create evidence)

| Priority | Sector ID | Reason |
|---|---|---|
| P0 | `ai_chips_gpu_dcu_asic` | No evidence YAML created in this phase |
| P1 | `ai_server_rack_supernode_switch` | No evidence YAML created in this phase |
| P1 | `aidc_data_center_compute_leasing` | No evidence YAML created in this phase |
| P1 | `liquid_cooling_thermal` | No evidence YAML created in this phase |
| P1 | `data_center_power_hvdc_ups` | No evidence YAML created in this phase |
| P1 | `high_speed_copper_connector` | No evidence YAML created in this phase |
| P1 | `ai_server_pcb_high_speed_board` | No evidence YAML created in this phase |
| P1 | `ccl_high_frequency_materials` | No evidence YAML created in this phase |
| P1 | `ic_substrate_abf_glass_tgv` | No evidence YAML created in this phase |
| P1 | `semiconductor_frontend_equipment` | No evidence YAML created in this phase |
| P1 | `semiconductor_metrology_test_equipment` | No evidence YAML created in this phase |
| P1 | `semiconductor_components_parts` | No evidence YAML created in this phase |
| P1 | `semiconductor_materials` | No evidence YAML created in this phase |
| P1 | `memory_hbm_ddr5` | No evidence YAML created in this phase |
| P1 | `advanced_packaging_chiplet_cowos_tsv` | No evidence YAML created in this phase |

---

## 5. Seed And Retired Output Checks

| Check | Result |
|---|---|
| Seed documents treated as evidence | ✅ No seed documents in `evidence_files[]` |
| Retired legacy outputs treated as active evidence | ✅ No retired outputs in `evidence_files[]` |
| Old sector cards registered as evidence | ✅ No old cards in `evidence_files[]` |
| Old total tables registered as evidence | ✅ No old tables in `evidence_files[]` |

---

## 6. Source Metadata Completeness Check

| Evidence File | Sources | Evidence Items | Missing URL | Missing Date | Missing Title |
|---|---|---|---|---|---|
| `high_speed_optical_modules.yaml` | 31 | 9 | 31 | 0 | 0 |
| `optical_components_fau_precision_optics.yaml` | 17 | 7 | 5 | 0 | 0 |
| **Total** | **48** | **16** | **36** | **0** | **0** |

### Source ID Details

**`high_speed_optical_modules.yaml` (31 sources, 9 evidence items):**
- `source_index[]` has 31 entries
- 14 duplicate BaoStock sources (3 time-stamp variants per company: 185911, 190729, 191111)
- All sources have `date` and `title` populated
- All sources lack `url` field (BaoStock/Tencent direct/local cache, not web-indexable)
- `evidence_items[]` has 9 items: 8 company items + 1 sector comparison item
- All evidence items use canonical `sector_id: cpo_optical_module_silicon_photonics`

**`optical_components_fau_precision_optics.yaml` (17 sources, 7 evidence items):**
- `source_index[]` has 17 entries
- 5 sources lack `url` (BaoStock/AKShare/local cache, CNINFO PDF paths lack direct URLs)
- 6 CNINFO annual report sources have `url` in the `path` field but not in `url` field
- `evidence_items[]` has 7 items: 6 company items + 1 sector comparison item
- All evidence items use canonical `sector_id: optical_chip_components`

⚠️ **WARNING (deferred to 1E-d-b):** 36 sources lack `url` field. This is expected for database/cache sources and CNINFO local PDF references. Not a blocker for this phase.

---

## 7. Audit Summary — `audit_evidence_bindings.py`

| Metric | Value |
|---|---|
| `ERROR` | **0** |
| `WARNING` | **18** |
| `INFO` | **12** |
| `evidence_file_count` | **2** |

### Warnings (18)

| Code | Count | Description |
|---|---|---|
| `LEGACY_SECTOR_ID_USED` | 2 | Evidence files keep legacy sector IDs for migration compatibility |
| `P0_P1_EVIDENCE_MISSING` | 15 | P0/P1 scoring sectors have no bound evidence YAML yet |
| `EVIDENCE_OVERRIDES_LEGACY_ONLY` | 1 | `evidence_overrides.py` retains legacy theme keys but is marked legacy-only |

### Infos (12)

| Code | Count | Description |
|---|---|---|
| `SECTOR_EVIDENCE_MISSING` | 12 | P2/P3 sectors have no bound evidence YAML yet |

---

## 8. Pipeline Readiness Audit — Evidence-Related Findings

| Severity | Count | Key Finding |
|---|---|---|
| BLOCKER | 0 | ✅ No blockers |
| HIGH | 0 | ✅ No high-severity issues |
| MEDIUM | 31 | Legacy hardcoded strings in pipeline files; source metadata warnings |
| LOW | 20 | Evidence schema warnings, mock output baseline ready |

Evidence-specific finding:
- `EVIDENCE_SCHEMA_READY`: Active evidence schema/source_id audit has ERROR=0 (files=2, sources=48, items=16).

---

## 9. `evidence_overrides.py` Downgrade Confirmation

```python
LEGACY_ONLY_EVIDENCE_REGISTRY = True
```

- Project-aware evidence binding now uses `load_project.resolve_evidence_files_for_sector()`.
- The legacy theme-name registry is retained only for backward compatibility.
- No new project-aware code should import `evidence_overrides.py` for evidence resolution.

---

## 10. Evidence Binding Table

```
high_speed_optical_modules.yaml
  → canonical sector_id: cpo_optical_module_silicon_photonics
  → legacy_sector_id: cpo_optical_module
  → via legacy_map: high_speed_optical_modules → cpo_optical_module_silicon_photonics
  → evidence_file_id: high_speed_optical_modules
  → evidence_items: 9 (8 companies + 1 sector comparison)
  → source_count: 31 (14 duplicate BaoStock timestamps, 17 unique)
  → canonical sector_id in evidence_items: cpo_optical_module_silicon_photonics ✅

optical_components_fau_precision_optics.yaml
  → canonical sector_id: optical_chip_components
  → legacy_sector_id: optical_components
  → via legacy_map: optical_components_fau_precision_optics → optical_chip_components
  → evidence_file_id: optical_components_fau_precision_optics
  → evidence_items: 7 (6 companies + 1 sector comparison)
  → source_count: 17
  → canonical sector_id in evidence_items: optical_chip_components ✅
```

---

## 11. Legacy Alias Resolution Table

| Input | Type | Resolved To | Via |
|---|---|---|---|
| `cpo_optical_module_silicon_photonics` | canonical sector_id | `high_speed_optical_modules.yaml` | sector_universe.evidence_file_ids → run_manifest.sector_id |
| `optical_chip_components` | canonical sector_id | `optical_components_fau_precision_optics.yaml` | sector_universe.evidence_file_ids → run_manifest.sector_id |
| `high_speed_optical_modules` | evidence_file_id alias | `high_speed_optical_modules.yaml` | run_manifest.evidence_file_id match |
| `optical_components_fau_precision_optics` | evidence_file_id alias | `optical_components_fau_precision_optics.yaml` | run_manifest.evidence_file_id match |
| `cpo_optical_module` | legacy_sector_id | `high_speed_optical_modules.yaml` | run_manifest.legacy_sector_id → canonical |
| `optical_components` | legacy_sector_id | `optical_components_fau_precision_optics.yaml` | run_manifest.legacy_sector_id → canonical |

---

## 12. Source ID / Source Metadata Check

| Check | Result | Severity |
|---|---|---|
| `source_id` present in all evidence items | ✅ All 16 items have `source_id` | — |
| `source_id` in `source_index[]` | ✅ All 48 sources have `source_id` | — |
| `url` field populated | ⚠️ 36/48 sources lack `url` (database/cache/local PDF) | **WARNING** (defer to 1E-d-b) |
| `date` field populated | ✅ All 48 sources have `date` | — |
| `title` field populated | ✅ All 48 sources have `title` | — |
| Duplicate `source_id` | ⚠️ 14 duplicate BaoStock timestamps (same data, different query times) | **WARNING** (defer to 1E-d-b) |
| Canonical `sector_id` in evidence items | ✅ All 16 items use canonical `sector_id` | — |
| Legacy `sector_id` in evidence items | None found | ✅ |

---

## 13. ERROR / WARNING / INFO Summary

| Severity | Count | Category |
|---|---|---|
| **ERROR** | **0** | — |
| **WARNING** | **18 + 2 source** | 15 P0/P1 missing evidence, 2 legacy sector IDs, 1 legacy-only evidence_overrides.py, 36 missing url in sources (deferred) |
| **INFO** | **12** | 12 P2/P3 missing evidence |

**Pipeline Readiness:**
- BLOCKER: 0
- HIGH: 0
- MEDIUM: 31 (legacy hardcoded strings — not evidence binding related)
- LOW: 20

---

## 14. Recommendations

### This Phase (1E-d-a) — ✅ COMPLETE

| Item | Status |
|---|---|
| Project-aware evidence binding established | ✅ |
| `resolve_evidence_files_for_sector()` working | ✅ |
| `run_manifest.yaml` evidence_files correct | ✅ |
| `sector_universe.yaml` evidence_file_ids correct | ✅ |
| Legacy alias resolution verified | ✅ |
| Seed documents not in evidence | ✅ |
| Retired outputs not in evidence | ✅ |
| `audit_evidence_bindings.py` running | ✅ |
| Audit report refreshed | ✅ |
| Source metadata status recorded | ✅ |

### Next Phase (1E-d-b) — evidence schema/source_id 规范化

| Priority | Task | Notes |
|---|---|---|
| P1 | Deduplicate BaoStock timestamp variants (14 duplicate source_ids) | Same data queried at 185911, 190729, 191111 |
| P1 | Populate `url` for CNINFO annual report sources | 6 CNINFO sources have PDF paths but no URL field |
| P2 | Standardize `path` vs `source_url` field naming | `source_index[]` uses `url`; `source_rows[]` uses `source_url` |
| P2 | Validate evidence YAML schema contract | Check `evidence.schema.yaml` conformance for all 2 files |
| P3 | Add `evidence_id` to source entries | Some source entries may lack `evidence_id` |

---

## 15. Validation Commands Run

```bash
# 1. Load project config (JSON)
python -m investment_system.pipelines.sector_research.load_project --project tech_ai_semiconductor --json
# Result: errors=0, evidence_file_count=2, seed_document_count=1

# 2. Dry-run paths
python -m investment_system.pipelines.sector_research.load_project --project tech_ai_semiconductor --dry-run-paths
# Result: 2 evidence files listed, 1 seed document, 29 sectors, 8 retired outputs

# 3. Pipeline readiness audit
python -m investment_system.pipelines.sector_research.audit_pipeline_readiness --project tech_ai_semiconductor
# Result: BLOCKER=0, HIGH=0, MEDIUM=31, LOW=20; EVIDENCE_SCHEMA_READY

# 4. Evidence binding audit
python -m investment_system.pipelines.sector_research.audit_evidence_bindings --project tech_ai_semiconductor
# Result: ERROR=0, WARNING=18, INFO=12, evidence_file_count=2
```

---

## 16. Next Stage Recommendation

**Recommended: Enter 1E-d-b (evidence schema/source_id 规范化).**

Rationale:
- Canonical evidence binding is fully in place with `ERROR=0`.
- The `audit_evidence_bindings.py` resolver is working correctly for both canonical and legacy inputs.
- The 2 active evidence files have 36 missing `url` fields and 14 duplicate `source_id` entries (BaoStock timestamp variants), which are source_id/schema normalization tasks for 1E-d-b.
- Pipeline readiness BLOCKER=0.
- No blockers for entering 1E-d-b.
