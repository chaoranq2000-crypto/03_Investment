# Stock Universe Coverage Audit Report

**Project:** tech_ai_semiconductor
**Generated:** 2026-06-21
**Phase:** 1E-c-b
**Universe status:** seed_pool / incomplete
**Audit tool:** `audit_stock_universe.py`

---

## 1. Baseline Before 1E-c-b

Baseline command:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.audit_stock_universe --project tech_ai_semiconductor
```

Baseline result:

| Metric | Count |
|---|---:|
| ERROR | 0 |
| WARNING | 11 |
| Listed stocks | 40 |
| Pending stocks | 28 |
| Reference companies | 3 |
| Coverage ok | 3 |
| Coverage thin | 11 |
| Coverage missing | 11 |
| Coverage exempt | 4 |

Baseline P0/P1 gaps:

| Sector ID | Priority | Listed | Pending | Baseline status |
|---|---:|---:|---:|---|
| ai_chips_gpu_dcu_asic | P0 | 3 | 3 | thin |
| ai_server_rack_supernode_switch | P1 | 2 | 3 | thin |
| aidc_data_center_compute_leasing | P1 | 0 | 2 | missing |
| liquid_cooling_thermal | P1 | 2 | 0 | thin |
| data_center_power_hvdc_ups | P1 | 0 | 0 | missing |
| high_speed_copper_connector | P1 | 0 | 1 | missing |
| ai_server_pcb_high_speed_board | P1 | 3 | 3 | thin |
| ccl_high_frequency_materials | P1 | 0 | 2 | missing |
| ic_substrate_abf_glass_tgv | P1 | 0 | 3 | missing |
| semiconductor_frontend_equipment | P1 | 4 | 3 | thin |
| semiconductor_metrology_test_equipment | P1 | 1 | 3 | thin |
| semiconductor_components_parts | P1 | 0 | 0 | missing |
| semiconductor_materials | P1 | 4 | 0 | thin |
| memory_hbm_ddr5 | P1 | 2 | 0 | thin |
| advanced_packaging_chiplet_cowos_tsv | P1 | 3 | 1 | thin |

Baseline duplicate/invalid-ref status:

| Check | Result |
|---|---|
| duplicate stock code | 0 ERROR |
| duplicate stock name | 0 ERROR |
| invalid stock sector refs | 0 ERROR |
| invalid pending sector refs | 0 ERROR |

---

## 2. Admission Rule Used In This Phase

Formal `stocks` entries in 1E-c-b were admitted only when all of the following were satisfied:

1. Company name exists in local seed sources, mainly `主线目录.md` or existing `pending_code_resolution`.
2. A-share code/name/listing status was matched through the A-share code-name list on 2026-06-21.
3. `sectors` uses canonical `sector_id`.
4. Entry includes `code`, `name`, `sectors`, `role`, `exposure_type`, `verification_status`, `source`, and `notes`.
5. Notes explicitly state that only code/name/listing status was checked; sector exposure remains pending for evidence stage.

This phase did not verify business exposure, customer orders, revenue purity, valuation, scoring, rating, or investment conclusion.

---

## 3. Promoted To Formal Stocks

From `pending_code_resolution` to formal `stocks`:

| Company | Code | Sector IDs |
|---|---|---|
| 景嘉微 | 300474.SZ | ai_chips_gpu_dcu_asic |
| 复旦微电 | 688385.SH | ai_chips_gpu_dcu_asic |
| 国芯科技 | 688262.SH | ai_chips_gpu_dcu_asic, eda_ip_design_service |
| 中科曙光 | 603019.SH | ai_server_rack_supernode_switch |
| 紫光股份 | 000938.SZ | ai_server_rack_supernode_switch |
| 中兴通讯 | 000063.SZ | ai_server_rack_supernode_switch, fiber_cable_hollow_core_dci |
| 润泽科技 | 300442.SZ | aidc_data_center_compute_leasing |
| 光环新网 | 300383.SZ | aidc_data_center_compute_leasing |
| 立讯精密 | 002475.SZ | high_speed_copper_connector, ai_pc_phone_glasses_earbuds |
| 崇达技术 | 002815.SZ | ai_server_pcb_high_speed_board, ic_substrate_abf_glass_tgv |
| 深南电路 | 002916.SZ | ai_server_pcb_high_speed_board, ic_substrate_abf_glass_tgv |
| 胜宏科技 | 300476.SZ | ai_server_pcb_high_speed_board, ic_substrate_abf_glass_tgv |
| 兴森科技 | 002436.SZ | ic_substrate_abf_glass_tgv, advanced_packaging_chiplet_cowos_tsv |
| 生益科技 | 600183.SH | ccl_high_frequency_materials |
| 南亚新材 | 688519.SH | ccl_high_frequency_materials |
| 华海清科 | 688120.SH | semiconductor_frontend_equipment |
| 盛美上海 | 688082.SH | semiconductor_frontend_equipment |
| 微导纳米 | 688147.SH | semiconductor_frontend_equipment |
| 广立微 | 301095.SZ | semiconductor_metrology_test_equipment, eda_ip_design_service |
| 长川科技 | 300604.SZ | semiconductor_metrology_test_equipment |
| 中科飞测 | 688361.SH | semiconductor_metrology_test_equipment |
| 乐鑫科技 | 688018.SH | edge_ai_soc_mcu |
| 晶晨股份 | 688099.SH | edge_ai_soc_mcu |
| 全志科技 | 300458.SZ | edge_ai_soc_mcu |

Added from local seed taxonomy after code/name/listing match:

| Company | Code | Sector IDs |
|---|---|---|
| 奥飞数据 | 300738.SZ | aidc_data_center_compute_leasing |
| 数据港 | 603881.SH | aidc_data_center_compute_leasing |
| 宝信软件 | 600845.SH | aidc_data_center_compute_leasing |
| 申菱环境 | 301018.SZ | liquid_cooling_thermal |
| 高澜股份 | 300499.SZ | liquid_cooling_thermal |
| 同飞股份 | 300990.SZ | liquid_cooling_thermal |
| 科华数据 | 002335.SZ | data_center_power_hvdc_ups |
| 科士达 | 002518.SZ | data_center_power_hvdc_ups |
| 易事特 | 300376.SZ | data_center_power_hvdc_ups |
| 英威腾 | 002334.SZ | data_center_power_hvdc_ups |
| 欧陆通 | 300870.SZ | data_center_power_hvdc_ups |
| 沃尔核材 | 002130.SZ | high_speed_copper_connector |
| 神宇股份 | 300563.SZ | high_speed_copper_connector |
| 兆龙互连 | 300913.SZ | high_speed_copper_connector |
| 新亚电子 | 605277.SH | high_speed_copper_connector |
| 生益电子 | 688183.SH | ic_substrate_abf_glass_tgv |
| 华正新材 | 603186.SH | ccl_high_frequency_materials |
| 金安国纪 | 002636.SZ | ccl_high_frequency_materials |
| 中英科技 | 300936.SZ | ccl_high_frequency_materials |
| 精测电子 | 300567.SZ | semiconductor_metrology_test_equipment |
| 富创精密 | 688409.SH | semiconductor_components_parts |
| 新莱应材 | 300260.SZ | semiconductor_components_parts |
| 正帆科技 | 688596.SH | semiconductor_components_parts |
| 国瓷材料 | 300285.SZ | semiconductor_components_parts |
| 三环集团 | 300408.SZ | semiconductor_components_parts |
| TCL中环 | 002129.SZ | semiconductor_materials |
| 北京君正 | 300223.SZ | memory_hbm_ddr5 |
| 东芯股份 | 688110.SH | memory_hbm_ddr5 |
| 普冉股份 | 688766.SH | memory_hbm_ddr5 |
| 甬矽电子 | 688362.SH | advanced_packaging_chiplet_cowos_tsv |

Corrected existing formal stock:

| Company | Before | After | Reason |
|---|---|---|---|
| 曙光数创 | 301171.SZ | 920808.BJ | A-share code-name list matched 曙光数创 to 920808; old code was not retained. |

---

## 4. Pending Kept

Remaining pending candidates:

| Company | Suggested sectors | Reason kept pending |
|---|---|---|
| 士兰微 | wafer_foundry_specialty_process | P2 scope; keep for later wafer/specialty-process completion. |
| 斯达半导 | wafer_foundry_specialty_process | P2 scope; keep for later wafer/specialty-process completion. |
| 歌尔股份 | ai_pc_phone_glasses_earbuds, edge_ai_soc_mcu | P2/terminal scope; P0/P1 completion does not require promotion now. |
| 华大九天 | eda_ip_design_service | P2 scope; historical code confusion with 概伦电子 already noted, leave for later EDA completion. |

---

## 5. Coverage Change

Final audit result:

| Metric | Baseline | Final |
|---|---:|---:|
| ERROR | 0 | 0 |
| WARNING | 11 | 3 |
| Listed stocks | 40 | 94 |
| Pending stocks | 28 | 4 |
| Coverage ok | 3 | 19 |
| Coverage thin | 11 | 3 |
| Coverage missing | 11 | 3 |
| Coverage exempt | 4 | 4 |

P0 coverage:

| Sector ID | Baseline | Final |
|---|---|---|
| ai_chips_gpu_dcu_asic | 3, thin | 6, ok |
| cpo_optical_module_silicon_photonics | 6, ok | 6, ok |
| optical_chip_components | 6, ok | 6, ok |

P1 coverage:

| Sector ID | Baseline | Final |
|---|---|---|
| ai_server_rack_supernode_switch | 2, thin | 5, ok |
| aidc_data_center_compute_leasing | 0, missing | 5, ok |
| liquid_cooling_thermal | 2, thin | 5, ok |
| data_center_power_hvdc_ups | 0, missing | 5, ok |
| high_speed_copper_connector | 0, missing | 5, ok |
| ai_server_pcb_high_speed_board | 3, thin | 6, ok |
| ccl_high_frequency_materials | 0, missing | 5, ok |
| ic_substrate_abf_glass_tgv | 0, missing | 5, ok |
| semiconductor_frontend_equipment | 4, thin | 7, ok |
| semiconductor_metrology_test_equipment | 1, thin | 5, ok |
| semiconductor_components_parts | 0, missing | 5, ok |
| semiconductor_materials | 4, thin | 5, ok |
| memory_hbm_ddr5 | 2, thin | 5, ok |
| advanced_packaging_chiplet_cowos_tsv | 3, thin | 5, ok |

All P0/P1 sectors now meet the minimum listed-stock coverage threshold.

---

## 6. Still Not Ready For Formal Research Production

Remaining WARNINGs are outside P0/P1 and are expected for this phase:

| Sector ID | Priority | Final status | Reason |
|---|---:|---|---|
| fiber_cable_hollow_core_dci | P2 | thin | Only 中兴通讯 is linked after this phase. |
| wafer_foundry_specialty_process | P2 | thin | 士兰微 / 斯达半导 remain pending. |
| ai_pc_phone_glasses_earbuds | P2 | thin | Only 立讯精密 is linked after this phase. |
| llm_aigc_agent_office | P2 | missing | Not in P0/P1 scope. |
| industry_ai_applications | P2 | missing | Not in P0/P1 scope. |
| data_elements_corpus_copyright_security | P2 | missing | Not in P0/P1 scope. |

Even though P0/P1 coverage is now structurally adequate, formal research production should not begin until evidence migration and output schema alignment are complete.

---

## 7. Integrity Checks

Final audit:

| Check | Result |
|---|---|
| duplicate stock code | 0 ERROR |
| duplicate stock name | 0 ERROR |
| invalid stock sector refs | 0 ERROR |
| invalid pending sector refs | 0 ERROR |
| over-broad stocks | 0 |

乐鑫科技 / 晶晨股份 handling:

| Company | Final code | Status |
|---|---|---|
| 乐鑫科技 | 688018.SH | Promoted; previous confusion with 688099.SH resolved. |
| 晶晨股份 | 688099.SH | Promoted; no duplicate code with 乐鑫科技. |

---

## 8. Next Step

Recommendation:

Proceed to **1E-d: evidence_overrides.py migration to canonical sector_id + evidence resolution from run_manifest/evidence_file_ids**.

Reason:

- P0/P1 stock universe structural coverage is now adequate.
- Duplicate and invalid-ref checks are clean.
- Remaining WARNINGs are P2 scope and do not block 1E-d.
- Formal sector cards, scoring, rating, total tables, and investment conclusions are still not allowed until evidence and output quality gates are upgraded.

---

**Note:** This is an engineering audit report, not an investment report. All newly added stocks are research-object candidates only. Sector exposure, customer/order evidence, valuation, and investment quality remain unverified.
