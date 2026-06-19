# 国信 API 管道

这里用于重新封装国信证券 API 的正式数据管道。

当前规则：

- 使用统一 Conda 环境：`C:\Projects\03_Investment\.conda\investment-system\python.exe`
- API key 从环境变量 `GS_API_KEY` / `GS_API_KEY_BACKUP` 或 `investment_system/config/.env.local` 读取
- 不再依赖旧子项目虚拟环境
- 不再依赖旧 memory 文件

后续建议封装：

```text
market_quotes.py      实时行情、组合行情
historical_quotes.py  历史行情
fund_flow.py          资金流
financials.py         财务三表
screening.py          选股查询
```
