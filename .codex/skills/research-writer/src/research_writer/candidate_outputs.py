"""Build isolated formal-candidate outputs for one project-aware sector.

This generator uses project configuration, stock_universe, and structured
evidence only. It does not call external data sources and does not write to the
formal publication output root.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from investment_system.core.project_loader import (
    WORKSPACE_ROOT,
    ProjectConfig,
    get_output_contract,
    get_sector,
    get_stocks_for_sector,
    load_project,
    resolve_evidence_files_for_sector,
    validate_output_record_shape,
)


CANDIDATE_STATUS = "FORMAL_CANDIDATE_REVIEW_ONLY"
NO_ADVICE = "NOT_INVESTMENT_ADVICE"
NOT_RATED = "NOT_RATED"


@dataclass(frozen=True)
class CandidatePaths:
    output_dir: Path
    run_id: str
    sector_card: Path
    company_table: Path
    sector_comparison_table: Path
    source_index: Path
    missing_data_log: Path
    conflict_data_log: Path
    score_table: Path
    metadata: Path

    @property
    def all_files(self) -> list[Path]:
        return [
            self.sector_card,
            self.company_table,
            self.sector_comparison_table,
            self.source_index,
            self.missing_data_log,
            self.conflict_data_log,
            self.score_table,
            self.metadata,
        ]


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _run_id() -> str:
    return datetime.now().strftime("%Y%m%d")


def get_formal_candidate_output_dir(config: ProjectConfig) -> Path:
    return (
        WORKSPACE_ROOT
        / "investment_system"
        / "research"
        / "projects"
        / config.project_id
        / "audits"
        / "formal_candidate_outputs"
    )


def get_candidate_paths(config: ProjectConfig, sector_id: str, run_id: str | None = None) -> CandidatePaths:
    rid = run_id or _run_id()
    out_dir = get_formal_candidate_output_dir(config)
    prefix = f"formal_candidate_{sector_id}_{rid}"
    return CandidatePaths(
        output_dir=out_dir,
        run_id=rid,
        sector_card=out_dir / f"{prefix}_sector_card.md",
        company_table=out_dir / f"{prefix}_company_table.csv",
        sector_comparison_table=out_dir / f"{prefix}_sector_comparison_table.csv",
        source_index=out_dir / f"{prefix}_source_index.csv",
        missing_data_log=out_dir / f"{prefix}_missing_data_log.csv",
        conflict_data_log=out_dir / f"{prefix}_conflict_data_log.csv",
        score_table=out_dir / f"{prefix}_score_table.csv",
        metadata=out_dir / f"{prefix}_metadata.json",
    )


def _assert_candidate_path(config: ProjectConfig, path: Path) -> None:
    target = path.resolve()
    candidate_dir = get_formal_candidate_output_dir(config).resolve()
    formal_root = config.output_root.resolve()
    legacy_output = (WORKSPACE_ROOT / "科技主线调研输出").resolve()
    if not str(target).startswith(str(candidate_dir)):
        raise RuntimeError(f"candidate output path is outside formal_candidate_outputs: {target}")
    if str(target).startswith(str(formal_root)) or str(target).startswith(str(legacy_output)):
        raise RuntimeError(f"candidate output path would write to formal output root: {target}")


def _field_order(config: ProjectConfig, output_type: str) -> list[str]:
    contract = get_output_contract(config, output_type)
    fields: list[str] = []
    for key in ("required_fields", "optional_fields"):
        for field in contract.get(key, []) or []:
            if field not in fields:
                fields.append(field)
    return fields


def _read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_sector_evidence(config: ProjectConfig, sector_id: str) -> dict[str, Any]:
    evidence_files = resolve_evidence_files_for_sector(config, sector_id)
    sources_by_id: dict[str, dict[str, Any]] = {}
    evidence_items: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []

    for ef in evidence_files:
        path = Path(str(ef.get("_resolved_path") or ef.get("path") or ""))
        if not path.exists():
            continue
        data = _read_yaml(path)
        files.append({
            "evidence_file_id": ef.get("evidence_file_id") or data.get("evidence_file_id", ""),
            "path": str(path),
            "source_count": len(data.get("source_index", []) or []),
            "evidence_item_count": len(data.get("evidence_items", []) or []),
        })
        for source in data.get("source_index", []) or []:
            sid = str(source.get("source_id", "")).strip()
            if sid:
                sources_by_id[sid] = source
        for item in data.get("evidence_items", []) or []:
            item_sector = item.get("sector_id")
            canonical_ids = data.get("canonical_sector_ids", []) or []
            if item_sector and item_sector != sector_id:
                continue
            if not item_sector and sector_id not in canonical_ids:
                continue
            evidence_items.append(item)

    used_source_ids = sorted({
        sid
        for item in evidence_items
        for sid in _source_ids(item)
        if sid
    })
    return {
        "files": files,
        "sources_by_id": sources_by_id,
        "evidence_items": evidence_items,
        "used_source_ids": used_source_ids,
    }


def _source_ids(item: dict[str, Any]) -> list[str]:
    values = item.get("source_ids")
    if isinstance(values, list):
        return [str(v) for v in values if str(v).strip()]
    if isinstance(values, str) and values.strip():
        return [v.strip() for v in values.split(",") if v.strip()]
    value = item.get("source_id")
    return [str(value)] if value else []


def _confidence(value: Any) -> str:
    text = str(value or "中").strip()
    allowed = {"高", "中高", "中", "中低", "低"}
    return text if text in allowed else "中"


def _source_type(value: Any) -> str:
    text = str(value or "other").strip()
    mapping = {
        "market_data": "database",
        "financial_data": "database",
        "legacy_migrated": "other",
        "script_query": "direct_api",
    }
    allowed = {
        "annual_report",
        "interim_report",
        "quarterly_report",
        "announcement",
        "investor_relations",
        "exchange_qa",
        "broker_report",
        "policy_file",
        "database",
        "direct_api",
        "user_provided",
        "verifiable_public_page",
        "other",
    }
    normalized = mapping.get(text, text)
    return normalized if normalized in allowed else "other"


def _item_by_subject(items: list[dict[str, Any]], subject_id: str, evidence_type: str | None = None) -> list[dict[str, Any]]:
    rows = [i for i in items if str(i.get("subject_id", "")) == subject_id]
    if evidence_type:
        rows = [i for i in rows if i.get("evidence_type") == evidence_type]
    return rows


def _ids(items: list[dict[str, Any]]) -> str:
    values = [str(i.get("evidence_id", "")) for i in items if i.get("evidence_id")]
    return ",".join(values)


def _source_id_text(items: list[dict[str, Any]]) -> str:
    values = sorted({sid for item in items for sid in _source_ids(item) if sid})
    return ",".join(values)


def _safe_claim_summary(item: dict[str, Any]) -> str:
    metrics = item.get("metrics_supported") or item.get("used_for") or []
    metrics_text = ",".join(str(v) for v in metrics[:8]) if isinstance(metrics, list) else str(metrics)
    evidence_type = item.get("evidence_type", "evidence")
    return f"{evidence_type}; metrics={metrics_text}; evidence_id={item.get('evidence_id', '')}"


def _trading_claim(item: dict[str, Any]) -> str:
    claim = str(item.get("claim", "")).strip()
    if claim:
        return claim.replace("\n", " ")
    return _safe_claim_summary(item)


def build_formal_candidate_records(config: ProjectConfig, sector_id: str) -> dict[str, Any]:
    sector = get_sector(config, sector_id)
    stocks = get_stocks_for_sector(config, sector_id)
    evidence = load_sector_evidence(config, sector_id)
    items = evidence["evidence_items"]
    generated_at = _now_iso()
    sector_name = sector.get("sector_name", sector_id)
    all_evidence_ids = ",".join(str(i.get("evidence_id")) for i in items if i.get("evidence_id"))
    all_source_ids = ",".join(evidence["used_source_ids"])

    company_rows: list[dict[str, Any]] = []
    card_company_rows: list[str] = []
    trading_lines: list[str] = []
    fundamentals_lines: list[str] = []
    source_rows: list[dict[str, Any]] = []

    for stock in stocks:
        code = stock.get("stock_code") or stock.get("code") or ""
        name = stock.get("stock_name") or stock.get("name") or code
        company_items = _item_by_subject(items, code)
        trading_items = _item_by_subject(items, code, "trading_heat_fact")
        source_ids = _source_id_text(company_items)
        evidence_ids = _ids(company_items)
        data_status = "source_backed_candidate" if source_ids and evidence_ids else "missing_logged"
        company_rows.append({
            "project_id": config.project_id,
            "sector_id": sector_id,
            "sector_name": sector_name,
            "research_group_id": sector.get("research_group_id", ""),
            "stock_code": code,
            "stock_name": name,
            "market": stock.get("market", "A股"),
            "role": stock.get("role", ""),
            "exposure_type": stock.get("exposure_type", ""),
            "coverage_status": "formal_candidate",
            "data_status": data_status,
            "financial_period": "evidence_as_labeled",
            "source_ids": source_ids or all_source_ids,
            "evidence_ids": evidence_ids,
            "missing_fields": "formal_scoring_disabled",
            "conflict_flags": "none_logged",
            "notes": f"{CANDIDATE_STATUS}; {NO_ADVICE}",
        })
        card_company_rows.append(
            f"| {code} | {name} | {stock.get('role', '')} | {stock.get('exposure_type', '')} | {data_status} | {evidence_ids or 'missing_logged'} |"
        )
        if company_items:
            fundamentals_lines.append(
                f"- {code} {name}: {_safe_claim_summary(company_items[0])}; source_ids={_source_id_text(company_items[:1])}"
            )
        if trading_items:
            trading_lines.append(f"- {code} {name}: {_trading_claim(trading_items[0])}; source_id={_source_id_text(trading_items[:1])}")

    for sid in evidence["used_source_ids"]:
        source = evidence["sources_by_id"].get(sid, {})
        linked_eids = [
            str(item.get("evidence_id", ""))
            for item in items
            if sid in _source_ids(item) and item.get("evidence_id")
        ]
        subject_id = sector_id
        subject_name = sector_name
        subject_type = "sector"
        if len(linked_eids) == 1:
            item = next((i for i in items if i.get("evidence_id") == linked_eids[0]), {})
            subject_id = str(item.get("subject_id") or sector_id)
            subject_name = str(item.get("subject_name") or sector_name)
            subject_type = "company" if item.get("subject_type") == "company" else "sector"
        source_rows.append({
            "project_id": config.project_id,
            "source_id": sid,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "subject_name": subject_name,
            "sector_id": sector_id,
            "claim_supported": f"Formal candidate evidence linkage for {sector_id}",
            "source_type": _source_type(source.get("source_type") or source.get("access_method")),
            "source_title": source.get("title") or source.get("source_title") or sid,
            "source_date": str(source.get("date") or source.get("source_date") or generated_at[:10]),
            "url_or_path": source.get("local_path") or source.get("url") or source.get("url_or_path") or "investment_system/research/evidence",
            "confidence": _confidence(source.get("reliability_level") or source.get("confidence")),
            "evidence_ids": ",".join(linked_eids),
            "extracted_fields": "structured_evidence",
            "notes": f"{CANDIDATE_STATUS}; source copied from active evidence YAML",
        })

    sector_items = [i for i in items if i.get("subject_id") == sector_id]
    core_logic = (
        f"本候选输出仅确认该 sector 已存在结构化产业逻辑/公司/估值/交易热度/风险 evidence。"
        f" 产业逻辑证据: {_ids(sector_items) or '见公司级 evidence 与 source_index'}。"
    )

    missing_data_flags = "formal_scoring_disabled,field_level_conflict_review_pending"
    if sector_id == "high_speed_copper_connector":
        missing_data_flags += ",named_customer_order_certification,ai_server_named_customer_300563"

    comparison = {
        "project_id": config.project_id,
        "sector_id": sector_id,
        "sector_name": sector_name,
        "research_group_id": sector.get("research_group_id", ""),
        "parent_chain": sector.get("parent_chain") or sector.get("research_group_id") or "tech_ai_semiconductor",
        "chain_position": sector.get("chain_position") or "formal_candidate_not_classified",
        "core_logic": core_logic,
        "source_ids": all_source_ids,
        "generated_at": generated_at,
        "leader_stocks": ",".join((s.get("stock_name") or s.get("name") or "") for s in stocks[:3]),
        "elastic_stocks": ",".join((s.get("stock_name") or s.get("name") or "") for s in stocks[3:]),
        "prosperity_score": "not_applicable",
        "prosperity_reason": f"score_placeholder; source_ids={all_source_ids}; evidence_ids={all_evidence_ids}",
        "earnings_certainty_score": "not_applicable",
        "earnings_certainty_reason": f"score_placeholder; source_ids={all_source_ids}; evidence_ids={all_evidence_ids}",
        "valuation_score": "not_applicable",
        "valuation_reason": f"score_placeholder; source_ids={all_source_ids}; evidence_ids={all_evidence_ids}",
        "trading_comfort_score": "not_applicable",
        "trading_comfort_reason": f"score_placeholder; trading_heat source-backed; source_ids={all_source_ids}; evidence_ids={all_evidence_ids}",
        "catalyst_score": "not_applicable",
        "catalyst_reason": f"score_placeholder; source_ids={all_source_ids}; evidence_ids={all_evidence_ids}",
        "purity_score": "not_applicable",
        "purity_reason": f"score_placeholder; source_ids={all_source_ids}; evidence_ids={all_evidence_ids}",
        "risk_control_score": "not_applicable",
        "risk_control_reason": f"score_placeholder; source_ids={all_source_ids}; evidence_ids={all_evidence_ids}",
        "total_score": "not_applicable",
        "action_rating": NOT_RATED,
        "rating_reason": f"{NO_ADVICE}; no formal rating generated",
        "suggested_action": CANDIDATE_STATUS,
        "missing_data_flags": missing_data_flags,
        "key_evidence": f"source-backed evidence_count={len(items)}; evidence_files={len(evidence['files'])}",
        "key_risk": "反证检查仅形成研究风险，不形成交易动作。",
        "evidence_ids": all_evidence_ids,
        "confidence_level": "中高",
    }

    score = {
        "project_id": config.project_id,
        "sector_id": sector_id,
        "sector_name": sector_name,
        "prosperity_score": "not_applicable",
        "prosperity_reason": comparison["prosperity_reason"],
        "earnings_certainty_score": "not_applicable",
        "earnings_certainty_reason": comparison["earnings_certainty_reason"],
        "valuation_score": "not_applicable",
        "valuation_reason": comparison["valuation_reason"],
        "trading_comfort_score": "not_applicable",
        "trading_comfort_reason": comparison["trading_comfort_reason"],
        "catalyst_score": "not_applicable",
        "catalyst_reason": comparison["catalyst_reason"],
        "purity_score": "not_applicable",
        "purity_reason": comparison["purity_reason"],
        "risk_control_score": "not_applicable",
        "risk_control_reason": comparison["risk_control_reason"],
        "total_score": "not_applicable",
        "rating": NOT_RATED,
        "rating_reason": f"{NO_ADVICE}; formal candidate does not enable production scoring",
        "source_ids": all_source_ids,
        "evidence_ids": all_evidence_ids,
        "data_status": "score_placeholder",
        "notes": CANDIDATE_STATUS,
        "score_version": "formal_candidate_placeholder_v1",
        "generated_at": generated_at,
    }

    missing_rows = [
        {
            "project_id": config.project_id,
            "output_type": "score_table",
            "sector_id": sector_id,
            "stock_code": "SECTOR",
            "stock_name": sector_name,
            "missing_field": "formal_scoring",
            "current_value": "not_applicable",
            "severity": "medium",
            "reason": "Formal production scoring is disabled in this phase; only score_placeholder is generated.",
            "source_ids": all_source_ids,
            "notes": CANDIDATE_STATUS,
            "status": "missing",
        },
        {
            "project_id": config.project_id,
            "output_type": "company_table",
            "sector_id": sector_id,
            "stock_code": "SECTOR",
            "stock_name": sector_name,
            "missing_field": "field_level_conflict_review",
            "current_value": "not_applicable",
            "severity": "low",
            "reason": "Candidate output did not perform manual field-level conflict adjudication.",
            "source_ids": all_source_ids,
            "notes": CANDIDATE_STATUS,
            "status": "missing",
        },
    ]
    if sector_id == "high_speed_copper_connector":
        missing_rows.extend(
            [
                {
                    "project_id": config.project_id,
                    "output_type": "company_table",
                    "sector_id": sector_id,
                    "stock_code": "SECTOR",
                    "stock_name": sector_name,
                    "missing_field": "named_customer_order_certification",
                    "current_value": "missing",
                    "severity": "medium",
                    "reason": "全股票池仍缺完整的具名客户合同、订单金额、客户证书文件和产品型号收入拆分。",
                    "source_ids": all_source_ids,
                    "notes": CANDIDATE_STATUS,
                    "status": "missing",
                },
                {
                    "project_id": config.project_id,
                    "output_type": "company_table",
                    "sector_id": sector_id,
                    "stock_code": "300563.SZ",
                    "stock_name": "神宇股份",
                    "missing_field": "ai_server_named_customer_300563",
                    "current_value": "missing",
                    "severity": "medium",
                    "reason": "神宇股份具备 AI 服务器适配线缆与 DAC/PCIe 产品证据，但缺具名 AI 服务器客户和订单金额。",
                    "source_ids": all_source_ids,
                    "notes": CANDIDATE_STATUS,
                    "status": "missing",
                },
            ]
        )

    conflict_rows = [
        {
            "project_id": config.project_id,
            "output_type": "formal_candidate_outputs",
            "sector_id": sector_id,
            "stock_code": "SECTOR",
            "stock_name": sector_name,
            "field": "cross_source_conflict",
            "conflicting_values": "none_logged_in_candidate_generation",
            "source_ids": all_source_ids,
            "severity": "low",
            "resolution_status": "no_conflict_logged",
            "notes": CANDIDATE_STATUS,
            "evidence_ids": all_evidence_ids,
        }
    ]

    card = {
        "project_id": config.project_id,
        "sector_id": sector_id,
        "sector_name": sector_name,
        "research_group_id": sector.get("research_group_id", ""),
        "priority": sector.get("priority", ""),
        "status": CANDIDATE_STATUS,
        "generated_at": generated_at,
        "source_ids": all_source_ids,
        "evidence_ids": all_evidence_ids,
        "missing_fields": ",".join(row["missing_field"] for row in missing_rows),
        "conflict_flags": "none_logged",
        "markdown": render_sector_card(
            config=config,
            sector=sector,
            evidence=evidence,
            company_rows=card_company_rows,
            fundamentals_lines=fundamentals_lines,
            trading_lines=trading_lines,
            comparison=comparison,
            score=score,
            missing_rows=missing_rows,
            conflict_rows=conflict_rows,
        ),
    }

    return {
        "sector_card": card,
        "company_table": company_rows,
        "sector_comparison_table": comparison,
        "source_index": source_rows,
        "missing_data_log": missing_rows,
        "conflict_data_log": conflict_rows,
        "score_table": score,
        "evidence_info": evidence,
    }


def render_sector_card(
    *,
    config: ProjectConfig,
    sector: dict[str, Any],
    evidence: dict[str, Any],
    company_rows: list[str],
    fundamentals_lines: list[str],
    trading_lines: list[str],
    comparison: dict[str, Any],
    score: dict[str, Any],
    missing_rows: list[dict[str, Any]],
    conflict_rows: list[dict[str, Any]],
) -> str:
    sector_id = sector.get("sector_id", "")
    sector_name = sector.get("sector_name", sector_id)
    evidence_file_lines = [
        f"- {f['evidence_file_id']}: {f['path']} (sources={f['source_count']}, evidence_items={f['evidence_item_count']})"
        for f in evidence["files"]
    ]
    source_lines = [
        f"- {row['source_id']}: evidence_ids={row['evidence_ids']}"
        for row in build_source_rows_for_card(config, sector_id, evidence)[:20]
    ]
    missing_lines = [
        f"- {r['missing_field']}: {r['reason']} (severity={r['severity']})"
        for r in missing_rows
    ]
    conflict_lines = [
        f"- {r['field']}: {r['conflicting_values']} ({r['resolution_status']})"
        for r in conflict_rows
    ]

    return "\n".join([
        "---",
        f"project_id: {config.project_id}",
        f"sector_id: {sector_id}",
        f"sector_name: {sector_name}",
        f"research_group_id: {sector.get('research_group_id', '')}",
        f"priority: {sector.get('priority', '')}",
        f"status: {CANDIDATE_STATUS}",
        f"generated_at: {score.get('generated_at', '')}",
        f"action_rating: {NOT_RATED}",
        f"suggested_action: {CANDIDATE_STATUS}",
        f"investment_conclusion: {NO_ADVICE}",
        "---",
        "",
        f"# {sector_name}",
        "",
        "本文件为正式候选 sector card，用于验证正式输出生成链路；不构成投资建议。",
        "",
        "## 1. 一句话结论",
        f"{NO_ADVICE}。该文件仅说明 `{sector_id}` 已可从结构化 evidence 生成候选输出，尚未形成正式研究结论。",
        "",
        "## 2. 产业逻辑",
        comparison["core_logic"],
        "",
        "## Evidence 文件清单",
        "\n".join(evidence_file_lines) if evidence_file_lines else "- missing",
        "",
        "## source_id/evidence_id 索引",
        "\n".join(source_lines) if source_lines else "- missing",
        "",
        "## 3. 股票池",
        "| 股票代码 | 公司名称 | 角色 | 暴露类型 | 数据状态 | evidence_ids |",
        "| --- | --- | --- | --- | --- | --- |",
        "\n".join(company_rows) if company_rows else "| - | - | - | - | missing | - |",
        "",
        "## 4. 基本面验证",
        "\n".join(fundamentals_lines) if fundamentals_lines else "- missing: no company-level fundamentals evidence item found.",
        "",
        "## 5. 估值",
        "- 估值字段仅来自现有 evidence 的 metrics_supported 与 source/evidence 索引；本阶段不启用正式估值评分。",
        f"- source_ids: {comparison.get('source_ids', '')}",
        f"- evidence_ids: {comparison.get('evidence_ids', '')}",
        "",
        "## 6. 交易热度",
        "\n".join(trading_lines) if trading_lines else "- missing: no trading_heat evidence item found.",
        "",
        "## 7. 催化剂",
        "- 催化剂字段仅作为 evidence-backed candidate review 输入；不形成交易指令。",
        f"- evidence_ids: {comparison.get('evidence_ids', '')}",
        "",
        "## 8. 风险与证伪信号",
        "- 风险字段仅作为研究风险记录；不形成交易动作。",
        "- 后续正式研究需要逐项复核公司级风险、订单持续性、客户集中度、供给扩张和技术路线变化。",
        "",
        "## 9. 反证检查",
        "- 估值透支风险：需继续以估值 evidence 与历史区间核实。",
        "- 交易热度过高风险：需继续跟踪换手率、成交额分位、均线偏离度。",
        "- 订单一次性或景气误判风险：需继续补充订单持续性 evidence。",
        "- 供给扩张风险：需继续补充产能扩张与价格竞争 evidence。",
        "- 技术路线变化风险：需继续跟踪 CPO/LPO/硅光与可插拔方案的产业验证。",
        "- 龙头受益与二三线跟随风险：需区分公司级份额、客户、产品代际和盈利质量。",
        "- 证据不足项：正式评分、字段级冲突复核、前瞻预测来源一致性仍需补充。",
        "",
        "## 10. 打分",
        f"- rating: {score['rating']}",
        f"- data_status: {score['data_status']}",
        "- score_placeholder: formal scoring is disabled for this phase.",
        f"- source_ids: {score['source_ids']}",
        f"- evidence_ids: {score['evidence_ids']}",
        "",
        "## 11. 最终评级",
        f"{NOT_RATED}。{NO_ADVICE}。本阶段不生成正式 A/B/C/D/E 评级。",
        "",
        "## 12. 缺失数据",
        "\n".join(missing_lines),
        "",
        "## conflict / counter-evidence",
        "\n".join(conflict_lines),
        "",
        "## quality gate 状态",
        "- candidate_directory_isolated: pending audit",
        "- source_id_evidence_id_closure: pending audit",
        "- no_investment_conclusion: pending audit",
        "- validate_outputs_compatibility: pending audit",
        "",
        "## 13. 来源索引",
        "详见配套 formal_candidate source_index CSV。",
        "",
    ])


def build_source_rows_for_card(config: ProjectConfig, sector_id: str, evidence: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sid in evidence["used_source_ids"]:
        linked_eids = [
            str(item.get("evidence_id", ""))
            for item in evidence["evidence_items"]
            if sid in _source_ids(item) and item.get("evidence_id")
        ]
        rows.append({"source_id": sid, "evidence_ids": ",".join(linked_eids)})
    return rows


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def validate_candidate_record_shapes(config: ProjectConfig, records: dict[str, Any]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for output_type in [
        "sector_card",
        "company_table",
        "sector_comparison_table",
        "source_index",
        "missing_data_log",
        "conflict_data_log",
        "score_table",
    ]:
        data = records.get(output_type)
        rows = data if isinstance(data, list) else [data]
        errors: list[str] = []
        warnings: list[str] = []
        for row in rows:
            if output_type == "sector_card":
                row = {k: v for k, v in row.items() if k != "markdown"}
            result = validate_output_record_shape(config, output_type, row or {})
            errors.extend(result.get("errors", []) or [])
            warnings.extend(result.get("warnings", []) or [])
        results[output_type] = {"errors": errors, "warnings": warnings}
    return results


def write_formal_candidate_files(
    config: ProjectConfig,
    sector_id: str,
    records: dict[str, Any],
    *,
    clean: bool = False,
    run_id: str | None = None,
) -> CandidatePaths:
    paths = get_candidate_paths(config, sector_id, run_id)
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    for path in paths.all_files:
        _assert_candidate_path(config, path)
    if clean:
        for path in paths.all_files:
            if path.exists():
                path.unlink()

    csv_outputs = {
        "company_table": paths.company_table,
        "sector_comparison_table": paths.sector_comparison_table,
        "source_index": paths.source_index,
        "missing_data_log": paths.missing_data_log,
        "conflict_data_log": paths.conflict_data_log,
        "score_table": paths.score_table,
    }
    for output_type, path in csv_outputs.items():
        data = records[output_type]
        rows = data if isinstance(data, list) else [data]
        _write_csv(path, _field_order(config, output_type), rows)

    paths.sector_card.write_text(records["sector_card"]["markdown"], encoding="utf-8")
    metadata = {
        "project_id": config.project_id,
        "sector_id": sector_id,
        "run_id": paths.run_id,
        "generated_at": records["sector_card"].get("generated_at"),
        "candidate_only": True,
        "investment_conclusion": NO_ADVICE,
        "action_rating": NOT_RATED,
        "suggested_action": CANDIDATE_STATUS,
        "files": {name: str(path) for name, path in csv_outputs.items()} | {"sector_card": str(paths.sector_card)},
        "evidence_files": records["evidence_info"]["files"],
        "shape_validation": validate_candidate_record_shapes(config, records),
    }
    paths.metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build isolated formal-candidate outputs for one sector.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--sector-id", required=True)
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--candidate-only", action="store_true")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(argv)

    if not args.candidate_only:
        print("ERROR: --candidate-only is required for this generator.")
        return 2

    config = load_project(args.project, create_dirs=False, strict=False, silent=True)
    records = build_formal_candidate_records(config, args.sector_id)
    shape = validate_candidate_record_shapes(config, records)
    error_count = sum(len(v["errors"]) for v in shape.values())
    if error_count:
        print("ERROR: candidate record shape validation failed.")
        print(json.dumps(shape, ensure_ascii=False, indent=2))
        return 1

    paths = write_formal_candidate_files(
        config,
        args.sector_id,
        records,
        clean=args.clean,
        run_id=args.run_id,
    )
    print("Formal candidate outputs written")
    print(f"project_id: {config.project_id}")
    print(f"sector_id: {args.sector_id}")
    print(f"run_id: {paths.run_id}")
    print(f"output_dir: {paths.output_dir}")
    for path in paths.all_files:
        print(f"wrote: {path}")
    warning_count = sum(len(v["warnings"]) for v in shape.values())
    print(f"shape_errors: {error_count}")
    print(f"shape_warnings: {warning_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
