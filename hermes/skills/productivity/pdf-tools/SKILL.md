---
name: pdf-tools
description: "全面 PDF 工具 — 创建（从 Markdown）、合并、拆分、添加水印/页眉/页脚、提取文字、查看元信息。覆盖 PDF 全生命周期操作。"
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [pdf, document, merge, split, watermark, conversion]
---

# PDF Tools Skill（PDF 全功能工具集）

## 概述

全面的 PDF 文档操作工具集，覆盖 PDF 的创建、编辑、合并、拆分、水印、文字提取和信息查看。

## 触发条件

- 需要**创建 PDF**（从文字/Markdown）
- 需要**合并多个 PDF**
- 需要**拆分 PDF**或提取某些页面
- 需要**添加水印**（机密、草稿等）
- 需要**添加页眉/页脚/页码**
- 需要**从 PDF 提取文字**
- 需要查看 PDF **元信息**（页数、尺寸、作者等）

## 前置条件

```bash
pip install pypdf fpdf2
```

## 脚本路径

`~/.hermes/skills/productivity/pdf-tools/scripts/pdf_tools.py`

## 命令速查

| 命令 | 用途 | 示例 |
|------|------|------|
| `create` | 从 Markdown 创建 PDF | `cat doc.md \| python pdf_tools.py create out.pdf --title "报告"` |
| `merge` | 合并多个 PDF | `python pdf_tools.py merge out.pdf a.pdf b.pdf c.pdf` |
| `split` | 拆分/提取页面 | `python pdf_tools.py split in.pdf ./pages/ --pages 1-3,5` |
| `watermark` | 添加水印文字 | `python pdf_tools.py watermark in.pdf out.pdf --text "机密"` |
| `header-footer` | 添加页眉页脚 | `python pdf_tools.py header-footer in.pdf out.pdf --header "Q3" --footer "第X页"` |
| `info` | 查看元信息 | `python pdf_tools.py info doc.pdf` |
| `to-text` | 提取文字 | `python pdf_tools.py to-text doc.pdf --output doc.txt` |

## 详细用法

### 1️⃣ 创建 PDF（从 Markdown/文字）

```bash
# 从 stdin 输入
cat <<'MD' | python ~/.hermes/skills/productivity/pdf-tools/scripts/pdf_tools.py create report.pdf --title "项目报告" --author "张三"
# 项目概述
本项目旨在提升系统安全性。

## 关键指标
- 完成率：95%
- 用户数：1,200
- 满意度：4.5/5

## 下一步计划
1. 系统升级
2. 安全审计
3. 用户培训
MD

# 从文件读取
python ~/.hermes/skills/productivity/pdf-tools/scripts/pdf_tools.py create report.pdf --title "报告" --file content.md
```

支持：`#` / `##` / `###` 标题、`-` 项目符号、`1.` 编号列表、`---` 分隔线、普通段落、自动页码。

### 2️⃣ 合并 PDF

```bash
python ~/.hermes/skills/productivity/pdf-tools/scripts/pdf_tools.py merge combined.pdf part1.pdf part2.pdf part3.pdf
```

### 3️⃣ 拆分/提取页面

```bash
# 每页拆成单个文件
python ~/.hermes/skills/productivity/pdf-tools/scripts/pdf_tools.py split doc.pdf ./pages/

# 提取指定页码范围
python ~/.hermes/skills/productivity/pdf-tools/scripts/pdf_tools.py split doc.pdf ./output/ --pages 1-3,5,7-9
```

### 4️⃣ 添加水印

```bash
python ~/.hermes/skills/productivity/pdf-tools/scripts/pdf_tools.py watermark draft.pdf draft-watermarked.pdf --text "草稿 - 非最终版"

# 大字水印
python ~/.hermes/skills/productivity/pdf-tools/scripts/pdf_tools.py watermark report.pdf report-final.pdf --text "CONFIDENTIAL" --size 48
```

### 5️⃣ 添加页眉/页脚

```bash
python ~/.hermes/skills/productivity/pdf-tools/scripts/pdf_tools.py header-footer report.pdf report-formatted.pdf --header "机密 - 请勿外传" --footer "第 X 页"
```

### 6️⃣ 查看 PDF 信息

```bash
python ~/.hermes/skills/productivity/pdf-tools/scripts/pdf_tools.py info document.pdf

python ~/.hermes/skills/productivity/pdf-tools/scripts/pdf_tools.py info document.pdf --json
```

### 7️⃣ 提取文字

```bash
python ~/.hermes/skills/productivity/pdf-tools/scripts/pdf_tools.py to-text document.pdf
python ~/.hermes/skills/productivity/pdf-tools/scripts/pdf_tools.py to-text document.pdf --output document.txt
```

## 结合其他技能

### 和 nano-pdf 配合
- `nano-pdf` — 修改 PDF 中的特定文字
- `pdf-tools` — 整体操作（合并/拆分/水印/创建）

### 和 hybrid-office 配合
- Word 文档转 PDF：用 `hybrid-office` 创建 Word → 用系统工具打印
- 或者直接 `pdf_tools.py create` 从 Markdown 生成 PDF（绕过 Word）

## 常见问题

1. **`pypdf` 或 `fpdf2` 未安装**
   ```bash
   pip install pypdf fpdf2
   ```

2. **中文显示为方框**
   - 系统已自动检测并使用 Noto Sans CJK 字体
   - 如果仍显示异常，检查 `/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc` 是否存在

3. **创建 PDF 时内容为空**
   - 确保通过 stdin 管道传入内容，而不是直接运行
   - 或使用 `--file content.md`

4. **合并时某些 PDF 无法读取**
   - 确保文件未被加密或损坏
   - 加密的 PDF 需要先解密

## 安全说明

本脚本会写入 PDF 文件到您指定的输出路径。所有文件操作都使用 `argparse` 解析的用户参数作为目标路径，不会自动覆盖系统文件。使用 stdin 接收内容时，建议仅传入可信数据源的内容。
