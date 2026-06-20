# 统一数据源配置

目标是把 AKShare、BaoStock 和 Tushare 放到同一个配置入口，避免每个子项目各自维护路径、token 和调用规则。

## 配置文件

主配置样例：

```text
investment_system/config/data_sources.example.toml
```

本地私有覆盖文件建议命名：

```text
investment_system/config/data_sources.local.toml
```

环境变量样例：

```text
investment_system/config/.env.example
```

本地真实密钥建议放在：

```text
investment_system/config/.env.local
```

不要把 `.env.local`、真实 token、API key 写入报告、日志或公开文件。

## 数据源定位

| 数据源 | 角色 | 是否需要 token | 建议用途 |
|---|---|---:|---|
| AKShare | 免费数据采集与缓存 | 否 | A 股快照、K 线、财务低频数据、实验验证 |
| BaoStock | 免费 A 股历史与基础数据 | 否 | 历史 K 线、复权因子、股票基础资料、指数成分、低频基本面 |
| Tushare Pro | 付费/积分制数据接口，经本地配置的 HTTP 中转地址访问 | 是 | 交易日历、基础资料、行情与财务补充数据 |

## 推荐优先级

| 任务 | 优先级 |
|---|---|
| 实时行情 | AKShare -> Tushare |
| 日 K 线 | BaoStock -> AKShare -> Tushare |
| 复权因子 | BaoStock -> AKShare -> Tushare |
| 股票基础资料 | BaoStock -> AKShare -> Tushare |
| 财务三表 | BaoStock -> AKShare -> Tushare -> 公司报告 |
| 资金流 | AKShare，或作为缺口记录后补采 |
| 股票筛选 | BaoStock -> AKShare -> Tushare |

## 接口失败后的补采规则

当 BaoStock、Tencent direct、AKShare、Tushare 都无法获得某项关键数据时，允许联网搜索补采，但不能绕过来源登记。

联网补采优先级：

1. 公司公告、年报、半年报、季报。
2. 投资者关系活动记录、业绩说明会。
3. 互动易、上证e互动、交易所问答。
4. 政府政策文件。
5. 可验证的同花顺/Choice类公开页面、券商研报摘要；不要假设有 Wind 或 iFind 数据库接口。
6. 权威媒体和产业媒体。

联网补采结果必须写入 `investment_system/research/evidence/`，并在 `数据来源索引.csv` 中保留可索引 `source_url`。如果网页不稳定，应同时保存本地缓存路径。

禁止把没有 URL、本地路径或原文摘录的数据写成确定事实。

## 环境变量

PowerShell 示例：

```powershell
$env:TUSHARE_TOKEN="your_tushare_token"
$env:TUSHARE_HTTP_URL="http://8.163.90.143:8686/"
$env:TUSHARE_DISABLE_PROXY="1"
```

或者把真实值写入本地 `.env.local`，然后由脚本加载。

当前配置：

- Tushare token 和 HTTP 中转地址统一从环境变量或 `investment_system/config/.env.local` 读取。
- `TUSHARE_DISABLE_PROXY=1` 时会在 Tushare client 初始化前清理 `HTTP_PROXY`、`HTTPS_PROXY`、`http_proxy`、`https_proxy`、`ALL_PROXY` 和 `all_proxy`。
- 旧 memory 文件已不再作为依赖。
- Tushare 已重新加入统一环境；正式调用建议通过 `investment_system/pipelines/tushare_client.py` 创建 client。

## Python 环境原则

当前统一投资体系环境：

```text
C:\Projects\03_Investment\.conda\investment-system\python.exe
```

该环境用于统一配置检查、AKShare、BaoStock 和后续正式数据管道。环境放在项目根目录 `.conda` 下，避免未来移动 `investment_system` 业务目录时破坏 Conda 环境。

当前研究资料目录：

```text
A股科技前两主线调研文件包
```

旧虚拟环境和旧子项目环境已删除。执行 Python 统一使用项目根目录 Conda 环境。

激活方式：

```powershell
conda activate "C:\Projects\03_Investment\.conda\investment-system"
```

也可以不激活，直接调用：

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\scripts\check_data_sources.py
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\pipelines\tushare_client.py --ping
```


## 检查配置

只读检查，不请求外网：

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\scripts\check_data_sources.py
```

这个检查会确认：

- 配置文件是否存在。
- 环境变量是否已设置。
- AKShare/BaoStock 模块是否可导入。
- Tushare 模块、token、中转 HTTP 地址和代理清理开关是否已配置。
