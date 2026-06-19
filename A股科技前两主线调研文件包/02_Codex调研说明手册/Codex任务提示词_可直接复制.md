# 可直接复制给 Codex 的任务提示词

我正在做 A股科技主线板块的系统调研，目标是找出当前最适合参与的细分方向，评价标准包括：上涨空间大、业绩兑现概率高、泡沫风险小、资金认可度高、未来催化明确。

请不要直接给买卖建议，而是先建立结构化调研数据库。

请读取我提供的文件：

```text
A股科技前两主线_板块细分方向母表.csv
A股科技前两主线_调研批次建议.md
Codex调研说明手册.md
```

请完成以下任务：

## 第一阶段：建立细分方向调研卡片

对母表中的每一个 sub_theme 生成一份 Markdown 调研卡片，内容包括：

1. 产业逻辑
2. 上中下游位置
3. 代表公司清单
4. 业绩兑现情况
5. 估值水平
6. 资金认可度
7. 未来催化
8. 泡沫风险
9. 风险与证伪信号
10. 初步评分

每条关键事实都要有来源、日期、链接和原文摘录。

## 第二阶段：建立公司级数据表

每个细分方向选择 3-8 家代表公司，建立公司级数据表，字段包括：

```text
stock_code, company_name, main_theme, sub_theme, chain_position,
market_cap, latest_price, pct_change_1m, pct_change_3m, pct_change_6m,
turnover_value_20d_avg, relative_strength_vs_index,
revenue_2024, revenue_2025, revenue_2026E, revenue_2027E,
net_profit_2024, net_profit_2025, net_profit_2026E, net_profit_2027E,
gross_margin_latest, net_margin_latest,
pe_ttm, pe_2026E, pe_2027E, ps_ttm, peg_2026E,
main_theme_revenue_exposure,
order_or_customer_evidence,
capacity_progress,
product_stage,
institution_forecast_change,
catalysts, risks,
data_source, source_date, source_url, confidence_level
```

如果某项数据无法确认，请写“缺失”，不要编造。

## 第三阶段：建立横向比较总表

输出：

```text
科技细分方向横向比较表.csv
代表公司财务估值总表.csv
数据来源索引.csv
缺失数据清单.md
冲突数据清单.md
调研日志.md
```

横向比较表需要包含：

```text
main_theme, sub_theme, chain_position,
industry_logic_summary,
performance_stage_score,
industry_prosperity_score,
upside_score,
bubble_safety_score,
fund_recognition_score,
catalyst_score,
total_score,
recommended_next_action,
key_evidence,
key_risks,
missing_data
```

## 第四阶段：质量要求

1. 优先使用公司公告、定期报告、投资者关系记录、交易所互动平台、权威数据终端和权威媒体。
2. 不要只复制研报结论，要保留硬数据。
3. 重点识别“收入占比低的伪概念公司”。
4. 区分“已兑现”“正在兑现”“送样验证”“纯概念”。
5. 保留缺失数据和冲突数据，不要强行填满。
6. 每个评分必须有证据支持。
