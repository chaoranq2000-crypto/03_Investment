"""Build research outputs for the high-speed optical module theme."""
from __future__ import annotations

import csv
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
TODAY = date.today().isoformat()
RAW = ROOT / "investment_system" / "data" / "raw"
PROCESSED = ROOT / "investment_system" / "data" / "processed" / "theme_research" / TODAY
OUT = ROOT / "科技主线调研输出"

COMPANIES = [
    {"code": "300308", "market": "SZ", "set_code": 0, "name": "中际旭创"},
    {"code": "300502", "market": "SZ", "set_code": 0, "name": "新易盛"},
    {"code": "300394", "market": "SZ", "set_code": 0, "name": "天孚通信"},
    {"code": "603083", "market": "SH", "set_code": 1, "name": "剑桥科技"},
    {"code": "002281", "market": "SZ", "set_code": 0, "name": "光迅科技"},
    {"code": "000988", "market": "SZ", "set_code": 0, "name": "华工科技"},
    {"code": "300570", "market": "SZ", "set_code": 0, "name": "太辰光"},
    {"code": "300548", "market": "SZ", "set_code": 0, "name": "博创科技"},
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def yuan_to_yi(value: str) -> str:
    if not value:
        return "缺失"
    return f"{float(value) / 100000000:.2f}"


def pct(value: str) -> str:
    if not value:
        return "缺失"
    return f"{float(value) * 100:.2f}%"


def latest_profit_row(rows: list[dict[str, str]]) -> dict[str, str]:
    return sorted(rows, key=lambda r: r.get("statDate", ""))[-1] if rows else {}


def annual_row(rows: list[dict[str, str]], year: str) -> dict[str, str]:
    matches = [r for r in rows if r.get("year") == year and r.get("quarter") == "4"]
    return matches[-1] if matches else {}


def daily_latest(rows: list[dict[str, str]]) -> dict[str, str]:
    return rows[-1] if rows else {}


def load_summary() -> dict[str, dict[str, str]]:
    path = PROCESSED / "高速光模块_company_market_summary.csv"
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return {row["stock_code"]: row for row in csv.DictReader(f)}


def build_company_table() -> list[dict[str, str]]:
    market_summary = load_summary()
    rows: list[dict[str, str]] = []
    for company in COMPANIES:
        code = company["code"]
        daily = read_json(RAW / "baostock" / "daily_kline" / TODAY / f"{code}.json")
        profit = read_json(RAW / "baostock" / "profit" / TODAY / f"{code}.json")
        drows = daily.get("rows", [])
        prows = profit.get("rows", [])
        latest_daily = daily_latest(drows)
        latest_profit = latest_profit_row(prows)
        row_2024 = annual_row(prows, "2024")
        row_2025 = annual_row(prows, "2025")
        latest_price = latest_daily.get("close", "缺失")
        total_share = latest_profit.get("totalShare", "")
        market_cap = "缺失"
        if latest_price != "缺失" and total_share:
            market_cap = f"{float(latest_price) * float(total_share) / 100000000:.2f}亿元"
        eps_ttm = latest_profit.get("epsTTM", "")
        pe_ttm = "缺失"
        if latest_price != "缺失" and eps_ttm and float(eps_ttm) != 0:
            pe_ttm = f"{float(latest_price) / float(eps_ttm):.2f}"

        summary = market_summary.get(code, {})
        rows.append(
            {
                "stock_code": code,
                "company_name": company["name"],
                "main_theme": "AI算力硬件",
                "sub_theme": "高速光模块",
                "chain_position": "中游核心",
                "market_cap": market_cap,
                "latest_price": latest_price,
                "pct_change_1m": summary.get("pct_change_1m", "缺失"),
                "pct_change_3m": summary.get("pct_change_3m", "缺失"),
                "pct_change_6m": summary.get("pct_change_6m", "缺失"),
                "turnover_value_20d_avg": summary.get("turnover_value_20d_avg", "缺失"),
                "relative_strength_vs_index": "缺失",
                "revenue_2024": yuan_to_yi(row_2024.get("MBRevenue", "")),
                "revenue_2025": yuan_to_yi(row_2025.get("MBRevenue", "")),
                "revenue_2026E": "缺失",
                "revenue_2027E": "缺失",
                "net_profit_2024": yuan_to_yi(row_2024.get("netProfit", "")),
                "net_profit_2025": yuan_to_yi(row_2025.get("netProfit", "")),
                "net_profit_2026E": "缺失",
                "net_profit_2027E": "缺失",
                "gross_margin_latest": pct(latest_profit.get("gpMargin", "")),
                "net_margin_latest": pct(latest_profit.get("npMargin", "")),
                "pe_ttm": pe_ttm,
                "pe_2026E": "缺失",
                "pe_2027E": "缺失",
                "ps_ttm": "缺失",
                "peg_2026E": "缺失",
                "main_theme_revenue_exposure": "缺失；待核实800G/1.6T/海外CSP收入占比",
                "order_or_customer_evidence": "缺失；待核实公告/投资者关系记录",
                "capacity_progress": "缺失；待核实公告/投资者关系记录",
                "product_stage": "已形成上市公司财务兑现迹象；细分产品阶段待公告核实",
                "institution_forecast_change": "缺失",
                "catalysts": "AI数据中心资本开支、高速率光模块迭代、海外CSP需求；待逐项证据化",
                "risks": "近3/6月涨幅较大、估值扩张、客户集中、技术路线迭代、收入暴露待核实",
                "data_source": "BaoStock daily_kline/profit; AKShare/Tushare fallback; Guosen skills disabled",
                "source_date": TODAY,
                "source_url": f"investment_system/data/raw/baostock/daily_kline/{TODAY}/{code}.json; investment_system/data/raw/baostock/profit/{TODAY}/{code}.json",
                "confidence_level": "中：行情/财务可用，主线收入暴露证据缺失",
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_outputs() -> None:
    """Compatibility wrapper for the old high-speed optical build entrypoint.

    The enriched fields now live in
    ``investment_system/research/evidence/high_speed_optical_modules.yaml`` and
    are merged by ``run_research.py``. Keep this legacy entrypoint callable, but
    route it through the standardized flow so it cannot overwrite the enriched
    output with placeholder values.
    """
    import subprocess
    import sys

    commands = [
        [sys.executable, str(ROOT / "investment_system" / "pipelines" / "run_research.py"), "--sub-theme", "高速光模块", "--skip-guosen"],
        [sys.executable, str(ROOT / "investment_system" / "pipelines" / "cleanup_outputs.py")],
        [sys.executable, str(ROOT / "investment_system" / "pipelines" / "validate_outputs.py"), "--sub-theme", "高速光模块"],
    ]
    for command in commands:
        subprocess.run(command, cwd=ROOT, check=True)
    return

    company_rows = build_company_table()
    write_csv(OUT / "00_总表" / "代表公司财务估值总表.csv", company_rows)

    comparison_rows = [
        {
            "main_theme": "AI算力硬件",
            "sub_theme": "高速光模块",
            "chain_position": "中游核心",
            "industry_logic_summary": "AI集群内部和数据中心互联带动高速光模块速率从800G向1.6T/更高速率迭代；本轮调研已用BaoStock确认代表公司财务和行情显著兑现，但尚未完成逐家公司800G/1.6T收入占比公告核验。",
            "representative_companies": "中际旭创、新易盛、天孚通信、剑桥科技、光迅科技、华工科技、太辰光、博创科技",
            "performance_stage_score": "4",
            "industry_prosperity_score": "4",
            "upside_score": "2",
            "bubble_safety_score": "1",
            "fund_recognition_score": "5",
            "catalyst_score": "4",
            "total_score": "66",
            "recommended_next_action": "深挖但不追高；优先核实收入暴露、客户/订单、估值历史分位",
            "key_evidence": "8家代表公司近6月涨幅42.80%-326.94%；中际旭创2025年收入382.40亿元、净利润115.80亿元，2026Q1净利润63.17亿元；新易盛2025年收入248.42亿元、净利润95.53亿元，2026Q1净利润27.74亿元。",
            "key_risks": "多数标的近3/6月涨幅巨大，主线收入暴露、订单客户、机构预期和估值历史分位仍缺失；存在拥挤和高估风险。",
            "missing_data": "800G/1.6T收入占比、海外CSP客户/订单、产能利用率、机构一致预期、估值历史分位、指数相对强弱",
            "source_index_refs": "SRC-BAO-DAILY-001; SRC-BAO-PROFIT-001; SRC-GUOSEN-DISABLED-001; SRC-AKSHARE-ERR-001",
        }
    ]
    write_csv(OUT / "00_总表" / "科技细分方向横向比较表.csv", comparison_rows)

    source_rows = [
        {
            "source_id": "SRC-BAO-DAILY-001",
            "source_type": "database",
            "source_name": "BaoStock query_history_k_data_plus",
            "source_date": TODAY,
            "source_url": f"investment_system/data/raw/baostock/daily_kline/{TODAY}/",
            "related_main_theme": "AI算力硬件",
            "related_sub_theme": "高速光模块",
            "related_company": "8家代表公司",
            "quote_or_excerpt": "字段包括date, open, high, low, close, volume, amount, turn, pctChg；用于计算近1/3/6月涨幅和20日平均成交额。",
            "data_fields_supported": "latest_price,pct_change_1m,pct_change_3m,pct_change_6m,turnover_value_20d_avg",
            "confidence_level": "高",
            "notes": "最新交易日为2026-06-18；2026-06-19为当前日期但未取得当日收盘数据。",
        },
        {
            "source_id": "SRC-BAO-PROFIT-001",
            "source_type": "database",
            "source_name": "BaoStock query_profit_data",
            "source_date": TODAY,
            "source_url": f"investment_system/data/raw/baostock/profit/{TODAY}/",
            "related_main_theme": "AI算力硬件",
            "related_sub_theme": "高速光模块",
            "related_company": "8家代表公司",
            "quote_or_excerpt": "字段包括pubDate, statDate, roeAvg, npMargin, gpMargin, netProfit, epsTTM, MBRevenue, totalShare。",
            "data_fields_supported": "revenue_2024,revenue_2025,net_profit_2024,net_profit_2025,gross_margin_latest,net_margin_latest,pe_ttm,market_cap",
            "confidence_level": "中高",
            "notes": "收入字段仅在半年报/年报行有值；Q1收入缺失。",
        },
        {
            "source_id": "SRC-GUOSEN-DISABLED-001",
            "source_type": "disabled_source",
            "source_name": "Guosen skills disabled",
            "source_date": TODAY,
            "source_url": f"investment_system/data/raw/guosen/",
            "related_main_theme": "AI算力硬件",
            "related_sub_theme": "高速光模块",
            "related_company": "8家代表公司",
            "quote_or_excerpt": "本地国信证券 skills 已卸载，不作为本项目默认数据源。",
            "data_fields_supported": "none",
            "confidence_level": "高",
            "notes": "如未来重新启用，需显式恢复 skill 和数据源配置。",
        },
        {
            "source_id": "SRC-AKSHARE-ERR-001",
            "source_type": "disabled_source",
            "source_name": "AKShare stock_zh_a_hist",
            "source_date": TODAY,
            "source_url": "push2his.eastmoney.com",
            "related_main_theme": "AI算力硬件",
            "related_sub_theme": "高速光模块",
            "related_company": "中际旭创",
            "quote_or_excerpt": "ProxyError/RemoteDisconnected；禁用代理后仍RemoteDisconnected。",
            "data_fields_supported": "none",
            "confidence_level": "高",
            "notes": "与当前环境下Eastmoney端点不稳定一致。",
        },
    ]
    write_csv(OUT / "00_总表" / "数据来源索引.csv", source_rows)

    missing_md = """# 缺失数据清单

| 细分方向 | 公司 | 缺失字段 | 已查来源 | 下一步建议 |
|---|---|---|---|---|
| 高速光模块 | 8家代表公司 | 800G/1.6T收入占比、海外CSP客户、订单可见度、产能利用率 | BaoStock、AKShare、Tushare | 查公司年报、半年报、投资者关系记录、互动易/上证e互动 |
| 高速光模块 | 8家代表公司 | 2026E/2027E收入利润、PE、PEG、估值历史分位 | BaoStock | 补用户提供数据、可验证公开预测页面或券商研报 |
| 高速光模块 | 8家代表公司 | 相对科技指数/创业板/科创50强弱 | BaoStock个股日线 | 补指数日线并计算相对强弱 |
| 高速光模块 | 8家代表公司 | 资金流、板块关联 | Guosen skills disabled | Guosen skills 已禁用，改用其它来源或列入缺口 |
"""
    (OUT / "99_日志" / "缺失数据清单.md").write_text(missing_md, encoding="utf-8")

    conflict_md = """# 冲突数据清单

| 细分方向 | 公司 | 冲突字段 | 来源A | 来源B | 当前处理 |
|---|---|---|---|---|---|
| 高速光模块 | - | - | - | - | 暂未发现可比来源间的数据冲突；Guosen skills 已禁用，AKShare不可达时需记录缺口。 |
"""
    (OUT / "99_日志" / "冲突数据清单.md").write_text(conflict_md, encoding="utf-8")

    log_md = f"""# 调研日志

## {datetime.now().isoformat(timespec="seconds")}

- 读取调研说明手册和母表，选择P0方向：高速光模块。
- 使用统一Conda环境：`C:/Projects/03_Investment/.conda/investment-system/python.exe`。
- BaoStock日线和利润数据已完成8家公司采集，原始数据保存在 `investment_system/data/raw/baostock/`。
- Guosen skills 已卸载，默认不读取 `GS_API_KEY`，不作为本轮事实来源。
- AKShare `stock_zh_a_hist` 触发Eastmoney远端断开，禁用代理后仍失败，暂不作为本轮事实来源。
- 已生成高速光模块调研卡片、横向比较表、代表公司财务估值总表、数据来源索引、缺失数据清单、冲突数据清单。
"""
    (OUT / "99_日志" / "调研日志.md").write_text(log_md, encoding="utf-8")

    company_lines = "\n".join(
        f"| {r['company_name']} | {r['stock_code']} | {r['chain_position']} | {r['main_theme_revenue_exposure']} | {r['data_source']} | {r['confidence_level']} |"
        for r in company_rows
    )
    card_md = f"""# 高速光模块

## 1. 结论摘要
- 当前主线地位：高
- 业绩兑现阶段：4分
- 估值水位：高
- 资金认可度：强
- 初步动作：深挖但不追高

## 2. 产业逻辑

高速光模块处于AI算力硬件的中游核心位置，受益于AI集群内部互联、数据中心交换网络升级和高速率光模块迭代。本轮已用BaoStock验证代表公司层面的收入、利润、股价与成交额明显放量，但尚未完成逐家公司800G/1.6T收入占比、海外CSP客户和订单可见度的公告级核验，因此产业逻辑结论暂定为“高主线性、中等置信”。

## 3. 上中下游位置
- 上游：光芯片、激光器、探测器、光器件、PCB/材料等。
- 中游：高速光模块、光引擎、硅光/CPO/LPO相关模块。
- 下游：云厂商、AI数据中心、交换机/服务器厂商。
- 与其他主线交叉：CPO/NPO/LPO/硅光、光芯片、数据中心交换机、AI服务器。

## 4. 代表公司清单
| 公司 | 代码 | 产业链位置 | 主线收入暴露 | 证据来源 | 备注 |
|---|---|---|---|---|---|
{company_lines}

## 5. 业绩兑现情况
- 已兑现收入：中际旭创2025年收入382.40亿元、净利润115.80亿元；新易盛2025年收入248.42亿元、净利润95.53亿元。8家公司完整数据见总表。
- 已有订单/客户/定点：缺失，需查公司公告、投资者关系记录和互动平台。
- 产能进展：缺失，需查公司公告和定期报告。
- 2026E/2027E业绩预期：缺失，需补机构一致预期。
- 关键证据摘录：BaoStock利润数据字段包括 `MBRevenue`、`netProfit`、`gpMargin`、`npMargin`、`epsTTM`；来源索引见 `SRC-BAO-PROFIT-001`。

## 6. 估值水平
- PE TTM：见 `代表公司财务估值总表.csv`。
- 2026E PE：缺失。
- 2027E PE：缺失。
- PEG：缺失。
- PS：缺失。
- 估值历史分位：缺失。
- 与同行对比：初步看板块内涨幅和估值分化较大，待补历史分位和一致预期。

## 7. 行情与资金认可度
- 近1月涨幅：代表公司区间为 -0.18% 至 80.85%。
- 近3月涨幅：代表公司区间为 7.88% 至 220.41%。
- 近6月涨幅：代表公司区间为 42.80% 至 326.94%。
- 成交额变化：20日平均成交额从48.85亿元至342.75亿元不等。
- 是否跑赢科技指数/创业板/科创50：缺失，需补指数日线。
- 是否出现放量加速或拥挤：初步判断拥挤度较高，尤其近3/6月涨幅过大的标的需谨慎。

## 8. 未来催化
- 产业催化：AI数据中心资本开支、高速率光模块迭代、海外CSP需求。
- 政策催化：缺失，待补。
- 公司催化：订单、客户验证、产能释放、定期报告。
- 财报催化：2026中报/三季报是否继续验证高增长。

## 9. 风险与证伪信号
- 估值风险：近3/6月涨幅较大，若盈利上修不足，估值透支风险高。
- 业绩风险：主线收入占比未核实，可能存在“光通信概念强但AI高速模块暴露不足”的公司。
- 技术路线风险：CPO/LPO/硅光等路线变化可能改变价值分配。
- 竞争风险：海外客户集中、价格下降、供应链竞争。
- 证伪信号：订单放缓、毛利率回落、海外CSP资本开支下修、股价放量滞涨但盈利预期不上修。

## 10. 初步评分
| 维度 | 分数 | 证据 |
|---|---:|---|
| 产业景气度 | 4 | 代表公司收入利润与股价成交明显放量，但主线收入暴露待核实 |
| 业绩兑现概率 | 4 | BaoStock显示多家公司2025年收入利润高增长，2026Q1利润继续兑现 |
| 上涨空间 | 2 | 多数代表公司近3/6月涨幅较大，赔率需要重新核算 |
| 泡沫安全分 | 1 | 光迅科技近6月涨幅326.94%，多股近6月翻倍，拥挤风险高 |
| 资金认可度 | 5 | 20日平均成交额显著放大，市场认可度强 |
| 催化强度 | 4 | AI数据中心和高速率迭代催化仍强，但需验证订单和客户 |
| 综合评分 | 66 | 按说明手册权重折算，因估值和缺失数据扣分 |
"""
    (OUT / "01_AI算力硬件" / "01_高速光模块.md").write_text(card_md, encoding="utf-8")


if __name__ == "__main__":
    write_outputs()

