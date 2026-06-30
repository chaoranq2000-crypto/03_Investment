# Handoff: workflow-stage-contract 重构交接

Date: 2026-06-30
From: Codex desktop thread
To: GitHub / 网页端 GPT 协作会话
Status: ready_for_next

## Current Objective

本次交接记录说明 `tech_ai_semiconductor` 项目的小范围工程重构：清理 `workflow_stages.yaml` 的阶段契约结构，新增 `quality-auditor workflow-stage-contract` 审计，并验证 stage runner 与 YAML 阶段顺序一致。此记录用于上传到 GitHub 后，让网页端 GPT 在不读取本地聊天上下文的情况下继续协作。

## Scope Boundary

- 没有删除、移动或覆盖正式研究输出目录：`C:\Projects\03_Investment\科技主线调研输出`
- 没有移动或修改 `investment_system/research/evidence/` 下的 evidence 文件
- 没有改研究内容、结论、评分、持仓建议或正式报告正文
- 本次只改项目工作流契约、质量审计入口和日志/交接说明

## What Changed

1. `workflow_stages.yaml` schema 收敛为单一阶段定义源：
   - 删除 `skill_cli_routing.stages` 这份重复的 stage route map
   - 新增 top-level `stage_order`
   - 保留 top-level `warning_only_rules`、`global_forbidden_outputs`、`stages`
   - 将每个 stage 的 `preferred_cli` 下沉到 `stages.<stage_name>.preferred_cli`
   - 调整 `stages` 映射顺序，使它与 `stage_order` 完全一致

2. 新增 `quality-auditor workflow-stage-contract` 审计：
   - 检查 YAML mapping 无重复 key
   - 检查 `stage_order` 与 `stages.keys()` 完全一致且顺序一致
   - 检查每个 stage 必须包含 `preferred_cli`、`description`、`writes`、`requires_sector_id`、`requires_manual_confirmation`、`formal_output_write`、`steps`
   - 检查每个 `preferred_cli` 指向的 `.codex/skills/*/scripts/cli.py` 文件存在
   - 检查 `formal_output_write=true` 必须同时 `requires_manual_confirmation=true`
   - 检查 `publish_sector_card_only` 必须 `publish_scope=sector_card_only` 且 `no_overwrite_required=true`
   - 检查 Python stage runner 的 `SUPPORTED_STAGES` 与 YAML `stage_order` 一致

3. `runtime-contract-check` 复用新的 workflow-stage contract 审计：
   - 避免 runtime check 和独立 workflow-stage 审计维护两套规则
   - 当前 runtime contract 输出会包含 workflow-stage contract 的 INFO/HIGH 结果

## Files To Read First

按顺序读这些 live 文件，不要用归档快照替代当前事实源：

1. `investment_system/research/projects/tech_ai_semiconductor/workflow_stages.yaml`
2. `.codex/skills/quality-auditor/src/quality_auditor/workflow_stage_contract.py`
3. `.codex/skills/quality-auditor/src/quality_auditor/runtime_contract_check.py`
4. `.codex/skills/quality-auditor/src/quality_auditor/commands.py`
5. `.codex/skills/sector-research-orchestrator/src/sector_research_orchestrator/stage_runner.py`

## Files Modified

- `.codex/skills/quality-auditor/SKILL.md`
- `.codex/skills/quality-auditor/src/quality_auditor/commands.py`
- `.codex/skills/quality-auditor/src/quality_auditor/runtime_contract_check.py`
- `investment_system/research/projects/tech_ai_semiconductor/workflow_stages.yaml`
- `investment_system/research/projects/tech_ai_semiconductor/project_journal/项目日志总索引.md`
- `investment_system/research/projects/tech_ai_semiconductor/project_journal/INDEX.md`

## Files Added

- `.codex/skills/quality-auditor/src/quality_auditor/workflow_stage_contract.py`
- `investment_system/research/projects/tech_ai_semiconductor/project_journal/handoffs/2026-06-30-workflow-stage-contract重构交接.md`

## Commands And Results

Run from repo root `C:\Projects\03_Investment` with the project runtime:

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe -m investment_system.core.project_loader --project tech_ai_semiconductor --json
```

Result: nonzero warning-only baseline; JSON included `errors: []` and `_load_status: "warning"`. In `scope_check`, this was captured as `exit_code: 3` and marked `blocking: False`.

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py runtime-contract-check --project tech_ai_semiconductor
```

Result: exit 0; `BLOCKER=0`, `HIGH=0`, `INFO=7`.

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py workflow-stage-contract --project tech_ai_semiconductor
```

Result: exit 0; `BLOCKER=0`, `HIGH=0`, `INFO=4`.

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\sector-research-orchestrator\scripts\cli.py run-stage --project tech_ai_semiconductor --stage scope_check
```

Result: exit 0; `blocking_count=0`.

```powershell
git diff --check
```

Result: exit 0; only Git CRLF normalization warnings appeared.

## Known Warnings

- Existing project loader warnings remain: six sector coverage warnings for thin/missing stock coverage. They predate this refactor and were not addressed here.
- `scope_check` child-process captured output showed Chinese mojibake in some printed text. The validation status and JSON semantics were still usable. This display issue was left out of scope.
- `project_journal/` is collaboration memory only. Do not treat this handoff as formal evidence or as a source for research claims.

## Web GPT Collaboration Prompt

可以把下面这段发给网页端 GPT：

```text
你正在协作 C:\Projects\03_Investment 的 tech_ai_semiconductor 项目。请先阅读当前 live 文件，不要依赖归档快照：
1. investment_system/research/projects/tech_ai_semiconductor/workflow_stages.yaml
2. .codex/skills/quality-auditor/src/quality_auditor/workflow_stage_contract.py
3. .codex/skills/quality-auditor/src/quality_auditor/runtime_contract_check.py
4. .codex/skills/quality-auditor/src/quality_auditor/commands.py
5. .codex/skills/sector-research-orchestrator/src/sector_research_orchestrator/stage_runner.py

本次已完成 workflow stage contract 小范围重构：preferred_cli 已下沉到每个 stage，stage_order 与 stages.keys() 对齐，新增 quality-auditor workflow-stage-contract 审计，并让 runtime-contract-check 复用该审计。

请保持边界：不要改正式研究输出，不要移动 evidence 文件，不要生成正式投资结论。若继续修改，请先运行 workflow-stage-contract，再运行 runtime-contract-check 和 scope_check。
```

## Exact Next Step

1. 如果只是复核本次改动，先运行：

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py workflow-stage-contract --project tech_ai_semiconductor
```

2. 如果继续调整 stage schema 或 stage runner，改完后依次运行：

```powershell
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py workflow-stage-contract --project tech_ai_semiconductor
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\quality-auditor\scripts\cli.py runtime-contract-check --project tech_ai_semiconductor
C:\Projects\03_Investment\.conda\investment-system\python.exe .codex\skills\sector-research-orchestrator\scripts\cli.py run-stage --project tech_ai_semiconductor --stage scope_check
```
