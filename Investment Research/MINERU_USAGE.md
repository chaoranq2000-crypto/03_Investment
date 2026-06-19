# MinerU PDF 解析说明

本项目需要使用 MinerU 解析 PDF 时，默认调用以下已有环境：

```text
C:\Projects\02_Research\01_Papers\mineru-zotero-local
```

不要将该 Python 环境整体复制到当前项目。直接调用该目录中的 MinerU Python 环境或可执行入口，避免复制虚拟环境后出现路径、DLL、模型缓存或脚本入口失效的问题。

## 推荐查找入口

在当前项目目录中执行：

```powershell
Get-ChildItem "C:\Projects\02_Research\01_Papers\mineru-zotero-local" -Recurse -Filter "python.exe" |
  Select-Object -First 10 FullName
```

查找 MinerU 命令入口：

```powershell
Get-ChildItem "C:\Projects\02_Research\01_Papers\mineru-zotero-local" -Recurse -Filter "magic-pdf.exe"
Get-ChildItem "C:\Projects\02_Research\01_Papers\mineru-zotero-local" -Recurse -Filter "mineru.exe"
```

## 调用原则

1. 当前项目的普通 Python 任务仍优先使用本项目本地虚拟环境：

```powershell
.\.venv\Scripts\python.exe
```

2. 只有 PDF 解析任务使用 `mineru-zotero-local` 中的 MinerU 环境。

3. 如需在脚本或命令中调用 MinerU，应使用明确的绝对路径，例如：

```powershell
& "C:\Projects\02_Research\01_Papers\mineru-zotero-local\.venv\Scripts\python.exe" -c "import sys; print(sys.executable)"
```

如果实际 MinerU 环境入口不在 `.venv\Scripts\python.exe`，以查找到的真实路径为准。

## 输出位置建议

当前项目中的 PDF 解析中间文件建议放在：

```text
tmp\pdfs
```

最终研究报告建议放在：

```text
reports
```

