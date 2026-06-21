# Evidence Binding Audit - Phase 1E-d-a

Project: `tech_ai_semiconductor`

Date: 2026-06-21

Scope: engineering audit only. This report records evidence binding metadata and resolver behavior. It is not an investment report, does not score sectors, and does not treat old evidence YAML files as research-grade outputs.

## 1. Baseline

- `evidence_overrides.py` kept a legacy `THEME_EVIDENCE_FILES` registry keyed by legacy theme names:
  - `高速光模块` -> `high_speed_optical_modules.yaml`
  - `光器件/FAU/精密光学` -> `optical_components_fau_precision_optics.yaml`
- `run_manifest.yaml` registered 2 `evidence_files`.
- `sector_universe.yaml` referenced 2 evidence ids through canonical sector entries.
- Local evidence YAML files present under `investment_system/research/evidence/`: 2.
- No seed document was registered as evidence.
- No retired legacy output was registered as active evidence.
- Loader JSON baseline: `errors=0`, `evidence_file_count=2`; existing warnings were stock-universe P2 coverage warnings.

## 2. Evidence Files

| evidence_file_id | canonical sector_id | legacy_sector_id | path | status | action | exists |
|---|---|---|---|---|---|---|
| `high_speed_optical_modules` | `cpo_optical_module_silicon_photonics` | `cpo_optical_module` | `investment_system/research/evidence/high_speed_optical_modules.yaml` | `indexed_existing_evidence` | `index_only` | yes |
| `optical_components_fau_precision_optics` | `optical_chip_components` | `optical_components` | `investment_system/research/evidence/optical_components_fau_precision_optics.yaml` | `indexed_existing_evidence` | `index_only` | yes |

## 3. Canonical Binding Result

- `high_speed_optical_modules` is bound to canonical sector `cpo_optical_module_silicon_photonics`.
- `optical_components_fau_precision_optics` is bound to canonical sector `optical_chip_components`.
- Both `evidence_file_id` values are present in `sector_universe.yaml` `evidence_file_ids`.
- Both `run_manifest.yaml` evidence entries use canonical `sector_id`.

## 4. Legacy Resolution Result

- `cpo_optical_module` resolves to `cpo_optical_module_silicon_photonics`; kept as migration metadata.
- `optical_components` resolves to `optical_chip_components`; kept as migration metadata.
- Legacy sector ids are warnings in the audit, not errors, because the final binding is canonical.

## 5. Sector Evidence Coverage

| status | sectors |
|---|---|
| ok | `cpo_optical_module_silicon_photonics`, `optical_chip_components` |
| missing | all other sectors currently have no bound evidence YAML |

## 6. Missing P0/P1 Evidence

P0/P1 sectors without bound evidence are expected warnings in this phase:

- `ai_chips_gpu_dcu_asic`
- `ai_server_rack_supernode_switch`
- `aidc_data_center_compute_leasing`
- `liquid_cooling_thermal`
- `data_center_power_hvdc_ups`
- `high_speed_copper_connector`
- `ai_server_pcb_high_speed_board`
- `ccl_high_frequency_materials`
- `ic_substrate_abf_glass_tgv`
- `semiconductor_frontend_equipment`
- `semiconductor_metrology_test_equipment`
- `semiconductor_components_parts`
- `semiconductor_materials`
- `memory_hbm_ddr5`
- `advanced_packaging_chiplet_cowos_tsv`

Reason: 1E-d-a only establishes project-aware evidence binding and audit. It does not create or rewrite evidence YAML files.

## 7. Seed And Retired Output Checks

- `seed_documents` remains `use_as_seed_only`; it is not used as evidence.
- `retired_legacy_outputs` remains `ignore_unless_explicitly_requested`; none is used as active evidence.
- Old sector cards, old total tables, old logs, and seed documents were not registered in `evidence_files`.

## 8. evidence_overrides.py Downgrade

- `evidence_overrides.py` is marked `LEGACY_ONLY_EVIDENCE_REGISTRY = True`.
- Project-aware evidence binding now uses `load_project.resolve_evidence_files_for_sector()`.
- The legacy theme-name registry is retained only for backward compatibility.

## 9. Audit Summary

`audit_evidence_bindings.py` result:

- `ERROR=0`
- `WARNING=18`
- `INFO=12`
- `evidence_file_count=2`

Warning categories:

- 2 legacy-sector compatibility warnings.
- 15 P0/P1 sector evidence-missing warnings.
- 1 `evidence_overrides.py` legacy-only compatibility warning.

## 10. Recommendation

Recommended next stage: `1E-d-b`.

Reason: canonical evidence binding and audit entry are now in place with `ERROR=0`, but the old evidence YAML schema/source_id layer is not normalized yet. Enter `1E-d-b` before `1E-e` if the next priority is evidence/source traceability; enter `1E-e` only when output field/schema alignment becomes the priority.
