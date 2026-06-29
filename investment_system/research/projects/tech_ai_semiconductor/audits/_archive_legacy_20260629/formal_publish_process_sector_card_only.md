# Sector-card-only Formal Publish Process

- process_name: `sector-card-only formal publish`
- project_id: `tech_ai_semiconductor`
- scope: single canonical sector only
- current_reference_sector: `cpo_optical_module_silicon_photonics`
- first_documented_at: 2026-06-22 19:18:42 +08:00

## 适用范围

本流程只适用于已经完成 formal candidate、gated formal staging、publish readiness、人工确认的单 sector sector card 发布。

当前允许发布的唯一正式文件类型是 `sector_card`。发布目标必须来自 project-aware loader 解析出的 sector card 路径。

本流程不适用于以下任务：

- 批量发布 29 个 sector。
- 发布第二个 sector 但未重新跑完整门禁。
- 发布 company table、sector comparison table、score table、source index、missing data log、conflict data log。
- 启用正式评分、A/B/C/D/E 建仓评级或交易动作建议。
- 覆盖任何既有正式输出文件。

## 前置条件

执行 sector-card-only 发布前，必须同时满足：

- `load_project --project tech_ai_semiconductor --json` 可以加载项目配置。
- readiness audit 的 `BLOCKER=0`、`HIGH=0`。
- target sector 的 evidence coverage 已达到 OK。
- formal candidate audit `ERROR=0`。
- gated formal audit `ERROR=0`。
- formal publish readiness audit `ERROR=0`。
- `source_id_closure=True`。
- `evidence_id_closure=True`。
- `no_investment_conclusion=True`。
- `score_placeholder=True` 或正式评分门禁已单独完成；当前阶段只能接受 `score_placeholder=True`。
- `validate_outputs --project tech_ai_semiconductor` exit code 为 0。
- 目标 sector card 文件不存在。
- 人工确认已经明确限定为 `publish_scope=sector_card_only`。

## 人工确认要求

真实发布必须由用户显式确认，并且确认文本需要包括：

- project_id 或明确的项目上下文。
- canonical `sector_id`。
- `publish_scope=sector_card_only`。
- 不允许发布总表。
- 不允许启用正式评分。
- 不允许生成投资建议。
- 不允许覆盖既有文件。

缺少上述任一约束时，只能执行 dry-run 或 publish readiness rehearsal。

## 允许发布的文件类型

仅允许：

- `sector_card`

当前 CPO sector card 的正式目标路径为：

`C:\Projects\03_Investment\科技主线调研输出\3_光通信\高速互连\P0_光模块_CPO_硅光.md`

## 禁止发布的文件类型

在本流程仍未升级前，禁止写入：

- `科技主线调研输出\00_总表\**`
- `科技主线调研输出\99_日志\**`
- company table
- sector comparison table
- source index
- missing data log
- conflict data log
- score table
- 其他 sector card

## 发布前门禁

发布前至少运行：

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.load_project --project tech_ai_semiconductor --json
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.audit_pipeline_readiness --project tech_ai_semiconductor
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.audit_gated_formal_outputs --project tech_ai_semiconductor --sector-id <sector_id>
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.audit_formal_publish_readiness --project tech_ai_semiconductor --sector-id <sector_id>
```

通过标准：

- readiness: `BLOCKER=0`, `HIGH=0`。
- gated formal audit: `ERROR=0`。
- publish readiness audit: `ERROR=0`。
- target sector card path exists: `False`。
- shared target outputs remain absent or unchanged。

## 发布命令

真实发布只允许使用显式 scope、显式 confirm、显式 no-overwrite：

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.prepare_formal_publish --project tech_ai_semiconductor --sector-id <sector_id> --publish-scope sector_card_only --confirm-publish --no-overwrite
```

默认行为必须保持 dry-run。没有 `--confirm-publish` 时不得写入最终正式目录。

## 发布后审计

发布后至少运行：

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.sector_research.audit_formal_publish_result --project tech_ai_semiconductor --sector-id <sector_id>
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.pipelines.validate_outputs --project tech_ai_semiconductor
```

发布后通过标准：

- formal sector card exists。
- formal sector card target equals release manifest target。
- source hash equals target hash。
- publish log exists。
- `publish_scope=sector_card_only`。
- no investment conclusion。
- score remains placeholder/not_applicable。
- non-sector outputs unchanged。
- validate_outputs exit code 0。

## Hash 校验

发布日志必须记录：

- source gated file。
- target formal file。
- source hash。
- target hash。
- file size。
- publish time。
- confirm_publish=True。
- overwrite=False。
- gates_passed=True。
- investment_advice=False。
- score_status=`score_placeholder_not_applicable`。

如果 source hash 与 target hash 不一致，发布结果审计必须失败，且不得继续扩展到其他文件。

## No-overwrite 规则

正式发布必须传入 `--no-overwrite`。如果目标 sector card 已存在，发布脚本必须拒绝写入。

本流程不支持覆盖式发布。若未来需要替换正式 sector card，应新增单独的 replacement gate，并要求人工确认、旧文件 hash 归档、变更说明和发布后复核。

## validate_outputs 要求

`validate_outputs --project tech_ai_semiconductor` 必须 exit 0。

当前 sector-card-only 阶段没有发布总表，因此 validate_outputs 仍可能报告 company CSV、comparison CSV、source index 未生成，并以 structural-only 模式通过。这不是阻塞项，但必须在审计报告中说明。

## warning-only exit code 处理

当前 `load_project --json` 可能出现 exit code 1，但 JSON 中 `errors=[]` 且 `_load_status=warning`。在本流程中，此类结果记录为 warning-only 非阻塞项。

后续需要统一 loader 的 exit code 语义，建议将 warning-only 与 fatal error 区分开，例如：

- fatal error: exit 1。
- warning-only: exit 3 或 exit 0 + structured warning。

在 exit code 语义统一前，发布门禁必须同时检查 exit code 和 JSON 内容，不得只凭 exit code 判断失败。

## 失败回滚原则

本流程默认不自动删除或批量清理文件。

如果发布前失败：

- 不写入最终正式目录。
- 保留 audit、manifest、log 供排查。

如果发布后审计失败：

- 立即停止扩展发布。
- 不发布总表、评分或第二个 sector。
- 记录失败原因、source hash、target hash、目标路径状态。
- 若确需移除误发布文件，必须由用户单独确认，并且只能一次处理一个明确路径的文件。

## 复制到第二个 sector 的条件

只有在以下条件全部满足时，才可把本流程复制到第二个 sector：

- 第二个 sector 的 evidence coverage 为 OK。
- 第二个 sector 已完成 formal candidate generation。
- formal candidate audit `ERROR=0`。
- promote 到 gated formal staging 成功。
- gated formal audit `ERROR=0`。
- publish readiness audit `ERROR=0`。
- 人工阅读验收无必须返工问题。
- 目标 sector card 路径不存在。
- 用户再次显式确认 `publish_scope=sector_card_only`。

当前最接近的候选 sector 可以是已达到 OK 的 `optical_chip_components`，但仍必须完整重跑上述单 sector 门禁。

## 仍禁止启用总表、评分、批量发布的条件

只要以下任一条件未满足，就继续禁止总表、评分和批量发布：

- company table append/merge writer 未完成独立门禁。
- sector comparison table append/merge writer 未完成独立门禁。
- source index 正式合并机制未完成去重和 source_id 唯一性审计。
- missing/conflict log 正式写入机制未完成 canonical writer routing。
- production scoring calculator 未完成 no-data safe mode。
- A/B/C/D/E 评级和 suggested_action 尚未建立独立投资建议隔离门禁。
- P0/P1 仍存在 MISSING evidence coverage sector。
- `load_project` warning-only exit code 语义尚未统一。

在这些条件补齐前，sector-card-only 是唯一允许的正式发布形态。
