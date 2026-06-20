# 板块深度调研工作流

目标：生成可直接用于投研阅读的 research-grade 深度报告，而不只是能跑通的数据卡片。

## 1. 输入识别

每次调研先读取：

- `A股科技前两主线调研文件包/02_Codex调研说明手册/Codex调研说明手册.md`
- `A股科技前两主线调研文件包/01_调研板块细分方向列表/A股科技前两主线_板块细分方向母表.csv`
- 目标细分方向对应的现有输出、evidence YAML、原始缓存和日志。

## 2. 数据采集顺序

1. 行情层：BaoStock、Tencent direct、AKShare、Tushare。
2. 财务层：BaoStock、AKShare、Tushare、公司报告。
3. 证据层：年报、半年报、季报、公告、投资者关系记录、互动易、上证e互动、政策文件、券商研报。
4. 预测层：用户提供数据、可验证公开预测页面、券商研报；不要假设有 Wind 或 iFind 数据库接口，无法取得时进入缺口清单。

AKShare 只做低频、小批量、限速采集。不要用 AKShare 做高频循环爬取。

## 3. 接口失败后的联网补采

当接口或本地缓存无法获得某个关键字段时，进入联网补采分支：

- 优先搜索公司公告、交易所公告、定期报告和投资者关系记录。
- 其次搜索互动易、上证e互动、政府政策文件。
- 再搜索券商研报摘要、终端一致预期页面、权威财经数据库页面。
- 普通媒体和社区观点只能作为线索，不能作为高置信事实源。

联网补采必须产出可索引来源：

```text
source_name
source_date
source_url
quote_or_excerpt
data_fields_supported
confidence_level
```

如果网页内容不可稳定访问，应保存本地摘录或原始缓存，并在 `source_url` 同时记录本地路径和原网页 URL。

## 4. Evidence 结构化

所有补齐事实写入 `investment_system/research/evidence/<theme_slug>.yaml`，而不是直接改最终 Markdown。

Evidence 至少覆盖：

- `company_overrides`：公司级业务暴露、客户订单、产能进展、产品阶段、预测与风险。
- `source_rows`：能写入 `数据来源索引.csv` 的来源记录。
- `logs`：缺失数据和冲突数据。
- `report_sections` 或 research-grade `card_markdown`：只有经过来源核验的正文才能覆盖自动生成报告。

调试级 evidence 不得用 `card_markdown` 覆盖最终 research-grade 报告。

## 5. 写作与交付

报告生成顺序：

```text
run_research.py -> cleanup_outputs.py -> validate_outputs.py --grade pipeline -> validate_outputs.py --grade research
```

research-grade 失败时，按失败类型回到对应下层 skill：

- 行情/成交额/相对强弱失败：`market-data-router`
- 收入/利润/毛利率/PE/PS 失败：`financial-data-router`
- 来源不足/断言无来源/正文浅：`evidence-miner`
- 2026E/2027E/PEG 混乱：`forecast-normalizer`
- 报告结构或输出 schema 问题：`research-writer`
- 验收规则漏检：`quality-auditor`

## 6. 最终交付标准

最终报告必须满足：

- 正文可以连续阅读，不能只是字段列表。
- 每家公司都有独立分析段落。
- 核心结论能追溯到本地缓存路径或网页 URL。
- 仍无法获得的数据进入缺失清单。
- 冲突来源进入冲突清单。
- 不给直接买卖建议，除非用户另行要求策略决策。
