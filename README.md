# 发票PDF合并（生成A4排版）

功能：选择多个PDF发票并合并为一个PDF，输出页面固定为A4，并提供两种预设排版。

- 竖版A4：每页上下两张发票
- 横版A4：每页四张发票（2×2，四个角）

想直接使用可以阅读[使用说明](使用说明.md)

## 运行（源码）

1. 安装 Python 3.10+（建议 3.11/3.12）
2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 启动：

```bash
python app.py
```

## 打包成 exe（Windows）

方式一：一键脚本（推荐）

生成目录版（推荐，稳定）：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_onedir.ps1
```

产物位于 `dist/InvoiceMerger/InvoiceMerger.exe`。

生成单文件版（一个exe）：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_onefile.ps1
```

产物位于 `release/InvoiceMerger.exe`。

一次性生成两种版本：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_all.ps1
```

说明：

- `dist/`：目录版输出（运行只需要整个 `dist/InvoiceMerger/` 文件夹）
- `release/`：单文件版输出（只需要 `release/InvoiceMerger.exe`）
- `build/`：PyInstaller 的中间产物，可随时删除，重新打包会自动生成

方式二：手动命令

安装 PyInstaller：

```bash
pip install pyinstaller
```

生成单文件 exe（无控制台窗口）：

```bash
python -m PyInstaller --noconsole --onedir --name InvoiceMerger app.py
```

生成产物位于 `dist/InvoiceMerger/InvoiceMerger.exe`（若该目录未被占用/锁定）。

## 说明

- 默认开启“兼容模式(渲染)”，会把每页先渲染成图片再排版，能解决部分电子发票里“章/下载次数”等元素作为注释层导致无法随页面移动的问题，但输出文件体积会更大。
- 关闭兼容模式则使用 `pypdf` 进行矢量合并，文件更小但对少数PDF可能会出现上述问题。
