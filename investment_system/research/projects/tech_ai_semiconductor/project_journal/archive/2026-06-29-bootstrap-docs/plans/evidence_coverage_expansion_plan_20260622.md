# Evidence Coverage Expansion Plan - Phase 1E-j-a

## Scope

This report is an engineering preparation artifact for selecting the third sector before any formal publication step.

Boundary confirmation:

- No third sector is published in this phase.
- No formal candidate output is generated.
- No gated formal output is generated.
- No release manifest is generated.
- No file is written under `C:\Projects\03_Investment\科技主线调研输出\`.
- No formal sector card, total table, log directory, source index, missing/conflict log, comparison table, or score table is generated.
- No formal score, A/B/C/D/E build-position rating, target price, position sizing, buy/sell/add/reduce/clear-position recommendation, or investment advice is generated.

## Published Sectors

| sector_id | sector_name | publication state | publish scope | result audit |
|---|---|---:|---|---|
| `cpo_optical_module_silicon_photonics` | 光模块/CPO/硅光 | published | `sector_card_only` | ERROR=0, WARNING=0, INFO=8 |
| `optical_chip_components` | 光芯片/激光器/光器件 | published | `sector_card_only` | ERROR=0, WARNING=0, INFO=8 |

## Current Evidence Coverage Overview

Evidence coverage audit command:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.audit_evidence_coverage --project tech_ai_semiconductor
```

Observed result:

| scope | value |
|---|---:|
| priorities checked | P0, P1 |
| sectors checked | 17 |
| P0 sectors | 3 |
| P1 sectors | 14 |
| coverage OK | 2 |
| PARTIAL | 0 |
| MISSING | 15 |
| evidence files counted by audit | 4 |
| source rows counted by audit | 43 |
| evidence items counted by audit | 28 |
| company evidence items counted by audit | 26 |

Current durable evidence files:

| evidence file | current binding |
|---|---|
| `investment_system/research/evidence/high_speed_optical_modules.yaml` | `cpo_optical_module_silicon_photonics` |
| `investment_system/research/evidence/optical_components_fau_precision_optics.yaml` | `optical_chip_components` |
| `investment_system/research/evidence/trading_heat_optical_chain.yaml` | `cpo_optical_module_silicon_photonics`, `optical_chip_components` |

## P0/P1 Coverage State

| priority | sector_id | sector_name | current_evidence_coverage | stock_coverage_status | evidence files | company evidence | blocking reason |
|---|---|---|---|---:|---:|---|
| P0 | `cpo_optical_module_silicon_photonics` | 光模块/CPO/硅光 | OK | adequate | 2 | 14 | minimum requirements satisfied |
| P0 | `optical_chip_components` | 光芯片/激光器/光器件 | OK | adequate | 2 | 12 | minimum requirements satisfied |
| P0 | `ai_chips_gpu_dcu_asic` | AI芯片/国产算力/GPU/DCU/ASIC | MISSING | adequate | 0 | 0 | no evidence file; insufficient company evidence; no financial, valuation, trading heat, or risk evidence |
| P1 | `high_speed_copper_connector` | 高速铜缆/DAC/AEC/连接器 | MISSING | adequate | 0 | 0 | no evidence file; insufficient company evidence; no financial, valuation, trading heat, or risk evidence |
| P1 | `ai_server_pcb_high_speed_board` | AI服务器PCB/高速通信板 | MISSING | adequate | 0 | 0 | no evidence file; insufficient company evidence; no financial, valuation, trading heat, or risk evidence |
| P1 | `ccl_high_frequency_materials` | CCL/高频高速材料/铜箔/树脂 | MISSING | adequate | 0 | 0 | no evidence file; insufficient company evidence; no financial, valuation, trading heat, or risk evidence |
| P1 | `ai_server_rack_supernode_switch` | AI服务器/整机柜/超节点/交换机 | MISSING | adequate | 0 | 0 | no evidence file; insufficient company evidence; no financial, valuation, trading heat, or risk evidence |
| P1 | `data_center_power_hvdc_ups` | 电源/UPS/HVDC/配电 | MISSING | adequate | 0 | 0 | no evidence file; insufficient company evidence; no financial, valuation, trading heat, or risk evidence |
| P1 | `liquid_cooling_thermal` | 液冷/温控/散热 | MISSING | adequate | 0 | 0 | no evidence file; insufficient company evidence; no financial, valuation, trading heat, or risk evidence |
| P1 | `aidc_data_center_compute_leasing` | AIDC/数据中心/算力租赁 | MISSING | adequate | 0 | 0 | no evidence file; insufficient company evidence; no financial, valuation, trading heat, or risk evidence |
| P1 | `ic_substrate_abf_glass_tgv` | IC载板/ABF/玻璃基板/TGV | MISSING | adequate | 0 | 0 | no evidence file; insufficient company evidence; no financial, valuation, trading heat, or risk evidence |
| P1 | `semiconductor_frontend_equipment` | 半导体前道设备 | MISSING | adequate | 0 | 0 | no evidence file; insufficient company evidence; no financial, valuation, trading heat, or risk evidence |
| P1 | `semiconductor_metrology_test_equipment` | 半导体检测/量测/测试设备 | MISSING | adequate | 0 | 0 | no evidence file; insufficient company evidence; no financial, valuation, trading heat, or risk evidence |
| P1 | `semiconductor_components_parts` | 半导体零部件 | MISSING | adequate | 0 | 0 | no evidence file; insufficient company evidence; no financial, valuation, trading heat, or risk evidence |
| P1 | `semiconductor_materials` | 半导体材料 | MISSING | adequate | 0 | 0 | no evidence file; insufficient company evidence; no financial, valuation, trading heat, or risk evidence |
| P1 | `memory_hbm_ddr5` | 存储芯片/HBM/DDR5 | MISSING | adequate | 0 | 0 | no evidence file; insufficient company evidence; no financial, valuation, trading heat, or risk evidence |
| P1 | `advanced_packaging_chiplet_cowos_tsv` | 先进封装/Chiplet/CoWoS/TSV | MISSING | adequate | 0 | 0 | no evidence file; insufficient company evidence; no financial, valuation, trading heat, or risk evidence |

## Classification

已发布 sector:

- `cpo_optical_module_silicon_photonics`
- `optical_chip_components`

已 OK 但未发布 sector:

- None.

P0/P1 中最接近 OK 的 PARTIAL sector:

- None. The current audit has PARTIAL=0. All non-published P0/P1 sectors are MISSING because no sector-specific evidence file is bound.

P0/P1 中仍 MISSING 的 sector:

- `ai_chips_gpu_dcu_asic`
- `high_speed_copper_connector`
- `ai_server_pcb_high_speed_board`
- `ccl_high_frequency_materials`
- `ai_server_rack_supernode_switch`
- `data_center_power_hvdc_ups`
- `liquid_cooling_thermal`
- `aidc_data_center_compute_leasing`
- `ic_substrate_abf_glass_tgv`
- `semiconductor_frontend_equipment`
- `semiconductor_metrology_test_equipment`
- `semiconductor_components_parts`
- `semiconductor_materials`
- `memory_hbm_ddr5`
- `advanced_packaging_chiplet_cowos_tsv`

P2 / observation-only:

- P2 sectors are deferred in this phase, including `fiber_cable_hollow_core_dci`, `wafer_foundry_specialty_process`, `eda_ip_design_service`, `edge_ai_soc_mcu`, `llm_aigc_agent_office`, `industry_ai_applications`, `data_elements_corpus_copyright_security`, and `ai_pc_phone_glasses_earbuds`.
- P3 observation-only sectors are exempt from this phase: `sixg_compute_network`, `satellite_internet`, `quantum_technology`, `xinchuang_domestic_software`.

## Third-Sector Candidate Comparison

| sector_id | sector_name | priority | current_evidence_coverage | stock_coverage_status | relation_to_existing_published_cards | missing_evidence_items | required_new_evidence_files | source_id_closure_difficulty | expected_gate_risk | recommended_next_sector | reason |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `high_speed_copper_connector` | 高速铜缆/DAC/AEC/连接器 | P1 | MISSING | adequate, 5 stocks | Same `optical_interconnect` group as both published cards; directly adjacent to short-distance AI interconnect and can reuse optical-chain demand context as context only. | sector logic, at least 3 company evidence items, financial evidence, valuation source, trading heat source, risk evidence | `high_speed_copper_connector.yaml`; optional `trading_heat_high_speed_copper_connector.yaml` | Medium. Company annual reports and exchange Q&A/announcements should close most fields; industry context must not be promoted without source-backed sector evidence. | Medium-low after evidence collection; lowest adjacency risk among candidates. | Yes | Best match to priority rule: P1, closest to published optical cards, adequate stock pool, limited concept drift, and feasible source closure without formal scoring. |
| `ai_server_pcb_high_speed_board` | AI服务器PCB/高速通信板 | P1 | MISSING | adequate, 6 stocks | Adjacent to AI server and optical module demand through high-speed boards, switches, and module/server PCB value chain; one step farther than copper cable. | sector logic, at least 3 company evidence items, financial evidence, valuation source, trading heat source, risk evidence | `ai_server_pcb_high_speed_board.yaml`; optional `trading_heat_ai_server_pcb_high_speed_board.yaml` | Medium. Annual reports are available, but AI-server-specific revenue exposure may require careful IR/Q&A or announcement evidence. | Medium. Higher risk of broad PCB claims leaking beyond AI server exposure. | No | Strong second choice, but exposure purity and AI-server attribution are harder to close than copper connector. |
| `ccl_high_frequency_materials` | CCL/高频高速材料/铜箔/树脂 | P1 | MISSING | adequate, 5 stocks | Upstream of PCB/server/optical hardware; related to high-speed PCB but less directly tied to the two already published optical cards. | sector logic, at least 3 company evidence items, financial evidence, valuation source, trading heat source, risk evidence | `ccl_high_frequency_materials.yaml`; optional `trading_heat_ccl_high_frequency_materials.yaml` | Medium-high. Need distinguish high-frequency/high-speed CCL from ordinary CCL and avoid material-price concept claims without source backing. | Medium-high. Purity and product mix claims are likely the main gate risk. | No | Good future candidate after PCB/copper, but the current evidence gap is broader and more product-mix sensitive. |

Other considered P1 sectors:

- `ai_server_rack_supernode_switch`: stock coverage adequate, but server/switch evidence may involve broader AI capex and customer/order claims; expected gate risk is higher.
- `data_center_power_hvdc_ups`: stock coverage adequate, but data-center-specific exposure and AI workload linkage require extra verification.
- `liquid_cooling_thermal`: stock coverage adequate, but liquid-cooling penetration and order visibility need careful source-backed confirmation.

## Recommended Third Sector

Recommended sector:

- `high_speed_copper_connector` - 高速铜缆/DAC/AEC/连接器

Recommendation rationale:

- It is P1 and belongs to the same `optical_interconnect` group as the two published cards.
- It is industrially adjacent to CPO/optical modules and optical components through AI data-center short-distance interconnect, switch bandwidth upgrade, DAC/AEC, and connector value-chain logic.
- The stock pool is adequate: 5 listed companies are already in `stock_universe.yaml`.
- Although current evidence coverage is MISSING, the gap is clean and mechanical: create sector-specific evidence binding, add company-level annual-report/announcement/IR evidence for at least three companies, add trading heat, valuation, and risk evidence.
- It can be prepared without enabling formal scores, ratings, or investment conclusions.
- It is less dependent on subjective concept mapping than AI server, AIDC, or liquid cooling, provided each company exposure claim is tied to annual report, announcement, or exchange Q&A evidence.

## Evidence Expansion Plan For `high_speed_copper_connector`

### Proposed Evidence Files

Final naming should follow the project evidence registry convention in `run_manifest.yaml` and `sector_universe.yaml`. The names below are planning names only and must not be treated as created evidence files.

| planned evidence file | target theme | target coverage | source_id slots to close after source retrieval |
|---|---|---|---|
| `investment_system/research/evidence/high_speed_copper_connector.yaml` | Sector logic and company evidence for high-speed copper cable, DAC/AEC, and high-speed connectors | sector logic; company positioning; revenue/profit evidence; order/customer or product-stage evidence; valuation source; risk evidence | annual-report source slot per covered company; announcement or exchange-QA source slot per covered company if annual report does not prove DAC/AEC exposure; sector-level industry/source slot; risk/source slot |
| `investment_system/research/evidence/trading_heat_high_speed_copper_connector.yaml` | Trading heat facts for the sector stock pool | price, 20/60-day return, turnover, amount, relative strength, data date, source metadata | market-data source slot for BaoStock/Tencent/AKShare/Tushare cache or query output; one evidence item per covered stock |

Important source_id discipline:

- Do not pre-create source_id values in this planning phase.
- Assign deterministic source_id only after the source document, URL, local cache path, or data cache path exists.
- Every planned source_id must map to one real source row and at least one evidence item before it is used in generated outputs.

### Company Coverage Targets

Minimum for coverage OK:

- At least 3 company evidence items.
- Prefer covering all 5 current stocks before formal publication review: 立讯精密, 沃尔核材, 神宇股份, 兆龙互连, 新亚电子.

Company evidence should cover:

- Whether high-speed cable, DAC, AEC, connector, backplane, or related AI data-center interconnect products are disclosed.
- Revenue exposure or product/business segment exposure when available.
- Product stage: R&D, sample, customer certification, mass production, shipment, or order.
- Customer/order claims only when supported by annual report, announcement, investor-relations record, exchange Q&A, or similarly verifiable source.
- Risk evidence, especially product validation uncertainty, customer concentration, technology-route substitution between copper and optical, and valuation/expectation risk.

### Evidence Types Needed

| evidence need | preferred source type | acceptable fallback | formal-use rule |
|---|---|---|---|
| company exposure | annual report, interim report, company announcement | investor-relations record, exchange Q&A | Must cite source row; notes in `stock_universe.yaml` are not formal evidence. |
| product stage / customer verification | announcement, annual report, exchange Q&A | investor-relations record | Customer names, certification, or order claims require direct source support. |
| sector logic | company reports across the stock pool, exchange Q&A, high-quality industry source | broker report used as secondary source | Seed documents may guide search but cannot become formal evidence. |
| financial data | annual/interim report, structured financial data source | missing-data log if not available | Period labels must distinguish actual, TTM, and forecast. |
| valuation data | market-data source, valuation data source, generated cache with data date | missing-data log if not available | No formal score or rating in this phase. |
| trading heat | BaoStock/Tencent/AKShare/Tushare cache or query output | missing-data log if source fails | Include data date and source metadata. |
| risk evidence | annual report risk factors, announcements, industry/source documents | broker risk section as secondary context | Risk statements must not imply an investment action. |

### Seed / Context Only

The following may guide evidence mining but cannot be used as formal evidence, score input, rating support, or investment conclusion:

- `主线目录.md`.
- Old retired outputs under `科技主线调研输出/00_总表` or `科技主线调研输出/99_日志`.
- Notes fields in `stock_universe.yaml`.
- Any unregistered draft Markdown copied by the user.
- Existing CPO/optical sector cards, except as navigation context for what source-backed chain logic needs to be re-collected for the copper sector.
- Broker/media summaries without source rows and source-date metadata.

### Forbidden Formal-Card Statements

The following must not enter any formal card or publication artifact:

- Buy, sell, build-position, add-position, reduce-position, clear-position, target-price, or position-sizing language.
- A/B/C/D/E build-position rating.
- Claims that a company is recommended, must be bought, is a target holding, or deserves a target price.
- Unsourced customer/order/qualification claims.
- Unsourced financial, forecast, PE, PEG, or market-share claims.
- Claims derived only from seed/context documents.

## Next Stage Recommendation

Proceed to a dedicated evidence-mining phase for `high_speed_copper_connector`.

Recommended next-stage boundary:

- Allowed: collect and structure source-backed evidence YAML under `investment_system/research/evidence/`, then update project evidence registry only after source rows are ready.
- Not allowed: formal candidate generation, gated formal generation, release manifest generation, publication to `科技主线调研输出`, formal scoring, or investment advice.

Suggested next-stage command framing:

```text
请执行“阶段 1E-j-b：high_speed_copper_connector evidence/source_id 闭环采集”。

只采集并结构化 evidence，不生成 formal candidate，不生成 gated formal，不发布第三张卡。
优先覆盖立讯精密、沃尔核材、神宇股份、兆龙互连、新亚电子中至少 3 家公司的年报/公告/互动问答 evidence，
并建立 sector logic、财务/估值、交易热度、风险 source_id slots 的闭环。
不得生成正式评分、评级、投资建议、目标价或仓位建议。
```
