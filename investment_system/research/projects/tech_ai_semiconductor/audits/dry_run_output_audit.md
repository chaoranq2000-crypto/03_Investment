# Dry-Run Output Audit — Phase 1E-f

**Project:** `tech_ai_semiconductor`

**Sector ID:** `cpo_optical_module_silicon_photonics`

**Audit Date:** 2026-06-22

**Phase:** 1E-f — 正式最小样本 sector card 生成 dry-run

**Scope:** Engineering dry-run output audit only. No formal research output is generated.

---

## 1. Summary

| Metric | Value |
|---|---|
| ERROR | 0 |
| WARNING | 0 |
| INFO | 2 |
| dry_run_file_count | 7 |
| pollution_count | 0 |
| dry_run_type_pass_count | 7 |
| evidence_file_count | 1 |
| stock_count | 6 |

**Status: PASS** — All dry-run outputs generated and validated successfully.

---

## 2. HIGH=1定位与处理结果

### 2.1 来源

| Rule ID | File | Line | Message |
|---|---|---|---|
| THEME_NAME_HARDCODED | tools/collect_high_speed_optical.py | - | '高速光模块' hardcoded as dataset name |
| HARDCODED_OUTPUT_PATH | tools/collect_high_speed_optical.py | - | Output path hardcoded relative to ROOT |

### 2.2 影响评估

| 影响项 | 是否影响 | 说明 |
|---|---|---|
| project-aware dry-run | **否** | `tools/` 不在项目感知模式调用路径中 |
| validate_outputs | **否** | 不涉及验证脚本 |
| 正式输出目录安全 | **否** | legacy-only 工具，不影响正式目录 |
| source_id/evidence_id 闭环 | **否** | 不涉及证据绑定 |
| 正式投研生产 | **否** | 仅 legacy 数据采集工具 |

### 2.3 处理方式

**Status: accept_as_legacy**

- `tools/collect_high_speed_optical.py` 是 legacy-only 数据采集脚本
- 不在 `run_research.py` 项目感知模式中被调用
- 不影响任何 project-aware 工作流
- 建议后续清理时标记为 deprecated，不主动重构

---

## 3. Dry-Run Output Directory

```
C:\Projects\03_Investment\investment_system\research\projects\tech_ai_semiconductor\audits\dry_run_outputs
```

**Isolation Status:**
- Dry-run outputs are isolated from formal output root (`科技主线调研输出/`)
- Files are written only to audit directory
- `_assert_audit_path` validates path constraints

---

## 4. Generated Dry-Run Files

| File | Output Type | Status |
|---|---|---|
| dry_run_cpo_optical_module_silicon_photonics_company_table.csv | company_table | Written |
| dry_run_cpo_optical_module_silicon_photonics_sector_comparison_table.csv | sector_comparison_table | Written |
| dry_run_cpo_optical_module_silicon_photonics_source_index.csv | source_index | Written |
| dry_run_cpo_optical_module_silicon_photonics_missing_data_log.csv | missing_data_log | Written |
| dry_run_cpo_optical_module_silicon_photonics_conflict_data_log.csv | conflict_data_log | Written |
| dry_run_cpo_optical_module_silicon_photonics_score_table.csv | score_table | Written |
| dry_run_cpo_optical_module_silicon_photonics_sector_card.md | sector_card | Written |

**Coverage: 7/7 output types = 100%**

---

## 5. Evidence 解析结果

| Field | Value |
|---|---|
| Evidence File Count | 1 |
| Evidence File | high_speed_optical_modules.yaml |
| sector_id | cpo_optical_module_silicon_photonics |
| Source Count | 23 |
| Evidence Item Count | 9 |

**Evidence Resolver:** `resolve_evidence_files_for_sector()` working correctly.

---

## 6. source_id/evidence_id 闭环结果

| Field | Status |
|---|---|
| source_ids 引用 | Real source_ids from evidence YAML |
| evidence_ids 引用 | Real evidence_ids from evidence YAML |
| source_index 定义 | Defined in source_index CSV |
| 闭环检查 | PASS |

**Evidence source_ids used:**
- BAO-STOCK-300308-20260619
- BAO-STOCK-300502-20260619
- CNINFO-AR-300394-20260407
- ... (real source_ids from evidence YAML)

---

## 7. stock_universe 引用结果

| Field | Value |
|---|---|
| Stock Count | 6 |
| Source | stock_universe.yaml |
| Sector ID | cpo_optical_module_silicon_photonics |

**Stocks from stock_universe.yaml:**
- 中际旭创 (300308.SZ)
- 新易盛 (300502.SZ)
- 天孚通信 (300394.SZ)
- 光迅科技 (002281.SZ)
- 华工科技 (000988.SZ)
- 太辰光 (300570.SZ)

---

## 8. No-Investment-Conclusion 检查结果

| Check | Status |
|---|---|
| action_rating | NOT_RATED |
| rating | NOT_RATED |
| suggested_action | DRY_RUN_ONLY |
| 正式建仓评级 | 无 |
| 投资建议 | 无 |
| DRY_RUN_MARKER 标记 | 存在 |

**Status: PASS** — No formal investment conclusions generated.

---

## 9. 正式目录污染检查结果

| Check | Result |
|---|---|
| Dry-run files in formal output root | 0 violations |
| Dry-run files in sector_cards | 0 violations |
| Dry-run files outside audit directory | 0 violations |
| Pollution count | 0 |

**Status: PASS** — No formal directory pollution detected.

---

## 10. validate_outputs 检查结果

| Check | Result |
|---|---|
| Project-aware mode | Activated |
| Output contract | 7 types loaded |
| Formal outputs | 0 (none exist yet) |
| Structural readiness | Passed |

**Status: PASS**

---

## 11. Findings

### INFO (2)

- `DRY_RUN_STOCKS_FROM_UNIVERSE`: Found 6 stocks from stock_universe.yaml for cpo_optical_module_silicon_photonics
- `DRY_RUN_EVIDENCE_FILES_RESOLVED`: Resolved 1 evidence files for cpo_optical_module_silicon_photonics

---

## 12. Recommendations

### Status: READY FOR NEXT PHASE

**Evidence:**
- ERROR=0 in dry-run output audit
- All 7 output types covered
- Evidence resolver working correctly
- stock_universe reference working correctly
- No investment conclusions generated
- No formal directory pollution
- validate_outputs supports project-aware mode
- HIGH=1 is legacy-only, accepted as risk

### Next Phase Recommendation: 1E-g

**P0/P1 evidence coverage plan 或正式单 sector 研究生成**

Rationale:
- Dry-run output pipeline is validated end-to-end
- Evidence → output → validate → audit minimum loop is closed
- Production gate mechanism is functional
- Ready to proceed to formal evidence expansion or single-sector research generation

---

## Appendix A: Validation Commands Results

| Command | Exit | Key Metrics |
|---|---|---|
| load_project --json | 3 (warning) | errors=0, _load_status=warning |
| audit_pipeline_readiness | 0 | BLOCKER=0, HIGH=1 (accept_as_legacy) |
| audit_evidence_bindings | 0 | ERROR=0, WARNING=18, INFO=12 |
| audit_evidence_schema | 0 | ERROR=0, WARNING=0, INFO=13 |
| audit_output_schema | 0 | ERROR=0, WARNING=3, INFO=3 |
| build_dry_run_outputs | 0 | 7 files written |
| **audit_dry_run_outputs** | 0 | **ERROR=0, WARNING=0, INFO=2** |
| validate_outputs | 0 | structural readiness passed |

---

## Appendix B: Evidence → Output → Validate → Audit Loop

```
evidence YAML (high_speed_optical_modules.yaml)
         ↓
resolve_evidence_files_for_sector()
         ↓
source_index[] + evidence_items[]
         ↓
build_dry_run_outputs.py
         ↓
dry_run CSV/MD files (isolated directory)
         ↓
audit_dry_run_outputs.py
         ↓
validate_outputs.py (structural check)
         ↓
Audit report
```

**Loop Status: CLOSED**
