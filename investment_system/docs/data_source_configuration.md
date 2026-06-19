# 统一数据源配置

目标是把 AKShare、国信证券 API 和 BaoStock 放到同一个配置入口，避免每个子项目各自维护路径、token 和调用规则。

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
| 国信证券 API | 实时行情与投研接口 | 是 | 实时行情、资金流、财务三表、智能选股 |
| BaoStock | 免费 A 股历史与基础数据 | 否 | 历史 K 线、复权因子、股票基础资料、指数成分、低频基本面 |

## 推荐优先级

| 任务 | 优先级 |
|---|---|
| 实时行情 | 国信 API -> AKShare |
| 日 K 线 | BaoStock -> AKShare -> 国信 API |
| 复权因子 | BaoStock -> AKShare |
| 股票基础资料 | BaoStock -> AKShare |
| 财务三表 | 国信 API -> BaoStock -> AKShare |
| 资金流 | 国信 API -> AKShare |
| 股票筛选 | 国信 API -> BaoStock -> AKShare |

## 环境变量

PowerShell 示例：

```powershell
$env:GS_API_KEY="your_guosen_key"
$env:GS_API_KEY_BACKUP="your_backup_guosen_key"
```

或者把真实值写入本地 `.env.local`，然后由脚本加载。

当前兼容旧项目：

- 国信 API key 统一从环境变量或 `investment_system/config/.env.local` 读取。
- 如主 key 触发限额，可切换到 `GS_API_KEY_BACKUP`。
- 旧 memory 文件已不再作为依赖。
- 新体系不复制国信 key 明文，避免出现多份密钥。
- Tushare 已从当前统一环境和配置中移除。

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

旧虚拟环境和旧子项目环境已删除。国信 API 后续通过 `investment_system/pipelines/guosen` 重新封装，执行 Python 统一使用项目根目录 Conda 环境。

激活方式：

```powershell
conda activate "C:\Projects\03_Investment\.conda\investment-system"
```

也可以不激活，直接调用：

```powershell
& "C:\Projects\03_Investment\.conda\investment-system\python.exe" investment_system\scripts\check_data_sources.py
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
- 国信 API 适配目录是否存在。
