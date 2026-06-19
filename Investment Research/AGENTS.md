# AGENTS.md instructions for C:\Projects\03_Investment\Investment Research

## 文件删除限制

禁止批量删除文件或目录。

不要使用：

- `del /s`
- `rd /s`
- `rmdir /s`
- `Remove-Item -Recurse`
- `rm -rf`

需要删除文件时，只能一次删除一个明确路径的文件。

正确示例：

```powershell
Remove-Item "C:\path\to\file.txt"
```

如果需要批量删除文件，应停止操作，并向用户请求，让用户手动删除。

## Python environment

Use a project-local virtual environment.

当前项目的普通 Python 任务优先使用：

```powershell
.\.venv\Scripts\python.exe
```

## MinerU PDF 解析

本项目需要使用 MinerU 解析 PDF 时，默认调用以下已有环境：

```text
C:\Projects\02_Research\01_Papers\mineru-zotero-local
```

不要将该 Python 环境整体复制到当前项目。直接调用该目录中的 MinerU Python 环境或可执行入口，避免复制虚拟环境后出现路径、DLL、模型缓存或脚本入口失效的问题。

PDF 解析任务是本项目本地 `.venv` 规则的例外：普通 Python 任务仍使用当前项目 `.venv`，只有 MinerU PDF 解析使用 `mineru-zotero-local` 环境。

推荐先查找真实入口：

```powershell
Get-ChildItem "C:\Projects\02_Research\01_Papers\mineru-zotero-local" -Recurse -Filter "python.exe" |
  Select-Object -First 10 FullName
```

查找 MinerU 命令入口：

```powershell
Get-ChildItem "C:\Projects\02_Research\01_Papers\mineru-zotero-local" -Recurse -Filter "magic-pdf.exe"
Get-ChildItem "C:\Projects\02_Research\01_Papers\mineru-zotero-local" -Recurse -Filter "mineru.exe"
```

调用示例：

```powershell
& "C:\Projects\02_Research\01_Papers\mineru-zotero-local\.venv\Scripts\python.exe" -c "import sys; print(sys.executable)"
```

如果实际 MinerU 环境入口不在 `.venv\Scripts\python.exe`，以查找到的真实路径为准。

PDF 解析中间文件建议放在：

```text
tmp\pdfs
```

最终研究报告建议放在：

```text
reports
```

