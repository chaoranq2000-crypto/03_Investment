# Tushare Proxy Smoke Test

- run_time: 2026-06-29T00:55:15
- base_url: https://fast.xiaodefa.cn
- token_length: 56
- ok: 22
- empty: 0
- error: 3

| api | status | rows | code | message/error | elapsed_ms |
|---|---:|---:|---:|---|---:|
| sdk_daily | OK | 9 |  |  | 499 |
| stock_basic | OK | 5530 | 0 |  | 416 |
| trade_cal | OK | 14 | 0 |  | 29 |
| daily | OK | 9 | 0 |  | 28 |
| daily_basic | OK | 9 | 0 |  | 29 |
| income | OK | 1 | 0 |  | 29 |
| balancesheet | OK | 1 | 0 |  | 296 |
| cashflow | OK | 1 | 0 |  | 29 |
| fina_indicator | OK | 2 | 0 |  | 38 |
| index_daily | OK | 9 | 0 |  | 30 |
| fund_basic | OK | 2844 | 0 |  | 194 |
| fund_daily | OK | 9 | 0 |  | 32 |
| cb_basic | OK | 1141 | 0 |  | 123 |
| fut_basic | OK | 3211 | 0 |  | 766 |
| opt_basic | OK | 12000 | 0 |  | 689 |
| moneyflow | OK | 9 | 0 |  | 30 |
| hk_basic | OK | 2751 | 0 |  | 448 |
| shibor | OK | 9 | 0 |  | 31 |
| report_rc | OK | 377 | 0 |  | 31 |
| research_report | ERROR |  | 40203 | 抱歉，您没有接口  research_report  访问权限 | 74 |
| anns_d | ERROR |  | 40203 | 抱歉，您没有接口  anns_d  访问权限 | 95 |
| irm_qa_sz | ERROR |  | 40203 | 抱歉，您没有接口  irm_qa_sz  访问权限 | 71 |
| ths_hot | OK | 100 | 0 |  | 32 |
| cn_gdp | OK | 176 | 0 |  | 97 |
| stk_mins | OK | 11 | 0 |  | 72 |
