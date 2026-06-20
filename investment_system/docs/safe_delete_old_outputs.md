# 安全删除旧产出计划

> 生成日期：2026-06-20
> 阶段：1E-clean
> 目的：在 project-aware 改造后，识别并安全清理旧项目产出，减少后续改造干扰

---

## 1. 旧产出文件分类清单

### 1.1 `科技主线调研输出/`（8 个文件）

| 文件 | 类型 | 大小 | 当前状态 | 建议操作 |
|---|---|---|---|---|
| `00_总表/代表公司财务估值总表.csv` | total_table | 25 KB | 已 retired | 可安全删除 |
| `00_总表/科技细分方向横向比较表.csv` | total_table | 3 KB | 已 retired | 可安全删除 |
| `00_总表/数据来源索引.csv` | total_table | 14 KB | 已 retired | 可安全删除 |
| `01_AI算力硬件/01_高速光模块.md` | sector_card | 15 KB | 已 retired | 可安全删除 |
| `01_AI算力硬件/01_光器件_FAU_精密光学.md` | sector_card | 14 KB | 已 retired | 可安全删除 |
| `99_日志/缺失数据清单.md` | log | 1 KB | 已 retired | 可安全删除 |
| `99_日志/冲突数据清单.md` | log | 0.2 KB | 已 retired | 可安全删除 |
| `99_日志/调研日志.md` | log | 3 KB | 已 retired | 可安全删除 |

> 注：整个 `科技主线调研输出/` 目录均可安全删除，因为新体系输出路径由 `output_spec.yaml` 的 `directories.root.path` 定义，不再依赖此目录。

### 1.2 `A股科技前两主线调研文件包/`（已不存在）

| 目录 | 状态 | 建议操作 |
|---|---|---|
| `A股科技前两主线调研文件包/` | 已由 git 标记删除 | 无需操作 |

### 1.3 `investment_system/data/raw/`（61 个文件）

| 子目录 | 文件数 | 内容 | 建议操作 |
|---|---|---|---|
| `akshare/financial_indicator/2026-06-20/` | 1 | AKShare 财务指标（300620） | 建议归档后删除 |
| `baostock/daily_kline/2026-06-19/` | 9 | BaoStock 日线（000988等） | 建议归档后删除 |
| `baostock/daily_kline/2026-06-20/` | 12 | BaoStock 日线（300308等+新增688xxx） | **保留**：今天采集的新数据 |
| `baostock/profit/2026-06-19/` | 7 | BaoStock 利润数据 | 建议归档后删除 |
| `baostock/profit/2026-06-20/` | 10 | BaoStock 利润数据 | **保留**：今天采集的新数据 |
| `diagnostics/2026-06-19/` | 1 | 数据源运行时诊断 | 可安全删除 |
| `evidence/2026-06-20/cninfo/` | 14 | CNINFO 年报 PDF + JSON 查询结果 | **保留**：属于 evidence 系统 |
| `research_runs/2026-06-19/` | 1 | run_meta.json | 可安全删除 |
| `research_runs/2026-06-20/` | 2 | run_meta.json × 2 | **保留**：最新运行元数据 |

### 1.4 `investment_system/research/evidence/`（2 个文件）

| 文件 | 大小 | 当前状态 | 建议操作 |
|---|---|---|---|
| `high_speed_optical_modules.yaml` | 47 KB | **仍被引用** | **暂不删除** — Phase 1E-d 前保留 |
| `optical_components_fau_precision_optics.yaml` | 38 KB | **仍被引用** | **暂不删除** — Phase 1E-d 前保留 |

---

## 2. 引用关系摘要

| 文件 | 被以下引用 | 解除引用后状态 |
|---|---|---|
| `科技主线调研输出/*` | run_manifest.yaml（已 retired）、loader（已排除 unregistered scan） | 无引用，可安全删除 |
| `data/raw/baostock/.../2026-06-19/` | run_research.py RAW_DIR（今天数据将覆盖） | 无直接引用，可安全删除 |
| `data/raw/baostock/.../2026-06-20/` | 仍在使用 | **保留** |
| `research/evidence/*.yaml` | evidence_overrides.py → load_theme_evidence() | **暂保留**（Phase 1E-d 后可删除） |

---

## 3. 可以安全删除的目录/文件

### 3.1 立即可删（无任何引用）

```powershell
# 1. 整个旧产出目录
Remove-Item -Recurse -Force "C:\Projects\03_Investment\科技主线调研输出"

# 2. 旧日期原始数据（不包含今天 2026-06-20）
Remove-Item -Recurse -Force "C:\Projects\03_Investment\investment_system\data\raw\baostock\daily_kline\2026-06-19"
Remove-Item -Recurse -Force "C:\Projects\03_Investment\investment_system\data\raw\baostock\profit\2026-06-19"
Remove-Item -Recurse -Force "C:\Projects\03_Investment\investment_system\data\raw\diagnostics"
Remove-Item -Recurse -Force "C:\Projects\03_Investment\investment_system\data\raw\research_runs\2026-06-19"
Remove-Item -Recurse -Force "C:\Projects\03_Investment\investment_system\data\processed\theme_research\2026-06-19"
```

### 3.2 建议归档后删除（有价值但不再需要）

```powershell
# 归档旧数据
Compress-Archive -Path "C:\Projects\03_Investment\investment_system\data\raw\baostock\daily_kline\2026-06-19" -DestinationPath "C:\Projects\03_Investment\_archive\baostock_daily_kline_2026-06-19.zip"
Compress-Archive -Path "C:\Projects\03_Investment\investment_system\data\raw\baostock\profit\2026-06-19" -DestinationPath "C:\Projects\03_Investment\_archive\baostock_profit_2026-06-19.zip"
```

---

## 4. 暂时不要删除的目录/文件

### 4.1 必须保留（直到 Phase 1E-d 完成）

- `investment_system/research/evidence/high_speed_optical_modules.yaml`
- `investment_system/research/evidence/optical_components_fau_precision_optics.yaml`

> 原因：`evidence_overrides.py` 的 `load_theme_evidence()` 仍通过 `THEME_EVIDENCE_FILES` 直接读取这两个文件。
> 将在 Phase 1E-d 中重构为从 `run_manifest.evidence_files` + `resolve_evidence_files_for_sector()` 读取。

### 4.2 必须保留（核心系统）

- `investment_system/research/projects/tech_ai_semiconductor/`（全部）
- `investment_system/pipelines/`（全部）
- `investment_system/research/templates/`
- `investment_system/research/schemas/`
- `investment_system/research/evidence/` 目录本身（YAML 文件见 4.1）
- `investment_system/data/raw/akshare/financial_indicator/2026-06-20/`（今天数据）
- `investment_system/data/raw/baostock/daily_kline/2026-06-20/`（今天数据）
- `investment_system/data/raw/baostock/profit/2026-06-20/`（今天数据）
- `investment_system/data/raw/evidence/`（CNINFO 年报证据）
- `investment_system/data/raw/research_runs/2026-06-20/`（今天元数据）

---

## 5. 删除前必须完成的解除引用项

| 解除引用项 | 负责阶段 | 当前状态 |
|---|---|---|
| `run_manifest.yaml` 中的 `existing_outputs` | 已完成（1E-clean） | ✅ 已改 `retired_legacy_outputs` |
| `load_project.py` 中 unregistered scan 对旧 sector card 的扫描 | 已完成（1E-clean） | ✅ 已排除 retired paths |
| `evidence_overrides.py` 中的 `THEME_EVIDENCE_FILES` | 1E-d | ⏳ 待处理 |
| `load_theme_evidence()` 调用 | 1E-d | ⏳ 待处理 |
| `data/raw/` 旧日期数据的 README 引用 | 无直接引用 | ✅ 无需处理 |

---

## 6. 删除后需要运行的验证命令

```powershell
# 1. Loader 仍然可以加载
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.load_project --project tech_ai_semiconductor --json

# 2. Pipeline readiness audit 无新增 BLOCKER
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.audit_pipeline_readiness --project tech_ai_semiconductor

# 3. validate_outputs 报告项目尚未运行（而非报错找不到旧文件）
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.validate_outputs --project tech_ai_semiconductor

# 4. dry-run paths 仍然正确
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.load_project --project tech_ai_semiconductor --dry-run-paths
```

期望结果：
- `load_project --json`：0 errors（允许 SECTOR_THIN_COVERAGE warning）
- `audit_pipeline_readiness`：BLOCKER = 0（允许 HIGH/MEDIUM 存在）
- `validate_outputs --project`：输出 `[PROJECT-AWARE] No output files exist for this project yet`（而非报错）

---

## 7. 删除步骤顺序

```
Step 1: 运行上述所有验证命令，记录当前状态
Step 2: 确认 retired_legacy_outputs 已正确标记在 run_manifest.yaml
Step 3: 删除整个 科技主线调研输出/ 目录
Step 4: 归档并删除 investment_system/data/raw/ 下的 2026-06-19 数据
Step 5: 运行验证命令，确认无 BLOCKER
Step 6: 完成 Phase 1E-d（解除 evidence YAML 引用）后，再删除 evidence YAML 文件
```

---

## 8. 文件大小汇总

| 目录 | 文件数 | 总大小 |
|---|---|---|
| `科技主线调研输出/` | 8 | ~65 KB |
| `data/raw/baostock/daily_kline/2026-06-19/` | 9 | ~390 KB |
| `data/raw/baostock/profit/2026-06-19/` | 7 | ~20 KB |
| `data/raw/diagnostics/` | 1 | 5 KB |
| `data/raw/research_runs/2026-06-19/` | 1 | 0.25 KB |
| `data/processed/theme_research/2026-06-19/` | 1 | 7.5 KB |
| **可删除合计** | **27** | **~490 KB** |
| `data/raw/evidence/`（保留） | 14 | ~23 MB |
| `data/raw/baostock/2026-06-20/`（保留） | 22 | ~800 KB |
