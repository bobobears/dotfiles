---
name: hybrid-office
description: "新建和编辑 Word 文档 (.docx) 与 Excel 工作簿 (.xlsx)。自动应用 Office 标准排版（字体/颜色/边框/页边距/隔行交替），输出符合企业规范的文档和表格。"
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [word, excel, docx, xlsx, office, document, spreadsheet, report]
    related_skills: [security-audit]
---

# Hybrid Office Skill（Word + Excel 文档技能）

## 概述

使用 `python-docx` 和 `openpyxl` 创建和编辑符合 Office 标准的专业 Word 文档和 Excel 工作簿。所有输出自动应用企业级排版规范。

## 触发条件

- 用户需要创建/编辑 **Word 文档**（.docx）
- 用户需要创建/编辑 **Excel 表格**（.xlsx）
- 用户提到"报告"、"文档"、"表格"、"报表"、"排版"等办公文档关键词
- 用户需要在报告中同时包含文字和表格数据

## 快速入门

### 前置条件

```bash
pip install python-docx openpyxl
```

### 核心脚本路径

所有脚本位于 `~/.hermes/skills/productivity/hybrid-office/scripts/`：

| 脚本 | 功能 |
|------|------|
| `create_word.py` | 创建新 Word 文档 |
| `edit_word.py` | 编辑已有 Word 文档 |
| `create_excel.py` | 创建新 Excel 工作簿 |
| `edit_excel.py` | 编辑已有 Excel 工作簿 |

---

## 一、创建 Word 文档

### 脚本调用

```bash
# 从 JSON 结构创建文档
cat <<'JSON' | python ~/.hermes/skills/productivity/hybrid-office/scripts/create_word.py output.docx
{
  "title": "项目报告",
  "subtitle": "2026年第二季度",
  "author": "张三",
  "sections": [
    {
      "heading": "项目概述",
      "level": 1,
      "paragraphs": [
        {"text": "本季度项目进展顺利，主要指标均达成预期目标。"},
        {"text": "关键里程碑", "bold": true, "text_after": "包括系统上线、用户验收测试通过。"},
        {"text": "已完成的需求项", "style": "bullet"},
        {"text": "待处理问题清单", "style": "bullet"},
        {"text": "优先处理事项", "style": "numbered"}
      ],
      "tables": [
        {
          "headers": ["指标", "目标值", "实际值", "完成率"],
          "rows": [
            ["系统上线数", "10", "12", "120%"],
            ["测试通过率", "95%", "98%", "103%"],
            ["用户满意度", "4.0", "4.5", "112%"]
          ],
          "caption": "表1: 季度关键指标"
        }
      ]
    }
  ]
}
JSON
```

### JSON 结构参考

详见 [references/word-structure.md](references/word-structure.md)

核心字段：
- `title` — 文档标题（封面页，26pt 深蓝加粗，居中）
- `subtitle` / `author` — 副标题（可选）
- `sections[]` — 章节列表
  - `heading` / `level` — 章节标题（1=一级, 2=二级, 3=三级）
  - `paragraphs[]` — 段落列表
    - `style`: `normal`(默认) / `bullet` / `numbered` / `quote`
    - `bold: true` — 粗体引导文字，配合 `text_after` 在同一段中继续普通文字
  - `tables[]` — 表格（自动蓝色表头 + 隔行交替色）

---

## 二、编辑 Word 文档

### 脚本调用

```bash
# 从 JSON 编辑指令修改文档
cat <<'JSON' | python ~/.hermes/skills/productivity/hybrid-office/scripts/edit_word.py input.docx output.docx
{
  "changes": [
    {"action": "replace_text", "old": "旧文字", "new": "新文字"},
    {"action": "add_paragraph", "text": "新增段落内容", "after_heading": "项目概述"},
    {"action": "add_table", "headers": ["A","B"], "rows": [["1","2"]]},
    {"action": "set_title", "text": "新标题"},
    {"action": "change_heading", "old": "旧标题", "new": "新标题"}
  ]
}
JSON
```

### 编辑动作说明

| action | 参数 | 说明 |
|--------|------|------|
| `replace_text` | old, new, occurrence? | 替换文档中的文字 |
| `add_paragraph` | text, after_heading? | 在指定标题后添加段落 |
| `add_table` | headers[], rows[] | 在末尾添加表格 |
| `set_title` | text | 修改文档一级标题 |
| `change_heading` | old, new | 修改指定标题文字 |

---

## 三、创建 Excel 工作簿

### 脚本调用

```bash
# 从 JSON 结构创建工作簿
cat <<'JSON' | python ~/.hermes/skills/productivity/hybrid-office/scripts/create_excel.py output.xlsx
{
  "title": "销售数据分析报告",
  "sheets": [
    {
      "name": "销售数据",
      "freeze_pane": "A2",
      "column_widths": [12, 20, 15, 12, 10],
      "title_cell": {
        "row": 1, "col": 1,
        "text": "2026年Q2销售数据",
        "merge_to": {"row": 1, "col": 5}
      },
      "tables": [
        {
          "headers": ["产品", "部门", "Q1销售额", "Q2销售额", "增长率"],
          "rows": [
            ["产品A", "华东区", "500,000", "650,000", "30%"],
            ["产品B", "华南区", "320,000", "410,000", "28%"],
            ["产品C", "华北区", "280,000", "350,000", "25%"]
          ],
          "start_row": 2
        }
      ],
      "summary_rows": [
        {"row_type": "after_table", "text": "合计: 1,410,000", "bold": true}
      ]
    }
  ]
}
JSON
```

### JSON 结构参考

详见 [references/excel-structure.md](references/excel-structure.md)

核心字段：
- `title` — 工作簿报告标题（非必须，仅用于描述）
- `sheets[]` — 工作表列表
  - `name` — 工作表名称
  - `freeze_pane` — 冻结窗格（如 `"A2"` 冻结首行）
  - `column_widths[]` — 列宽，不指定则自动适配
  - `title_cell` — 合并单元格标题（18pt 深蓝加粗）
  - `tables[]` — 数据表格
    - `headers` — 表头（白色粗体、深蓝背景、居中）
    - `rows` — 数据行（隔行交替浅蓝背景）
    - `start_row` — 起始行号
  - `summary_rows[]` — 汇总行（自动加顶部分隔线）

---

## 四、编辑 Excel 工作簿

### 脚本调用

```bash
cat <<'JSON' | python ~/.hermes/skills/productivity/hybrid-office/scripts/edit_excel.py input.xlsx output.xlsx
{
  "changes": [
    {"action": "update_cell", "sheet": "销售数据", "row": 3, "col": 2, "value": "新数值"},
    {"action": "add_row", "sheet": "销售数据", "data": ["新产品","新区域","100,000","150,000","50%"], "after_row": 5},
    {"action": "rename_sheet", "old": "Sheet1", "new": "分析结果"},
    {"action": "add_sheet", "name": "汇总"}
  ]
}
JSON
```

### 编辑动作说明

| action | 参数 | 说明 |
|--------|------|------|
| `update_cell` | sheet, row, col, value | 更新指定单元格 |
| `update_cell_by_header` | sheet, header, row, value | 按表头名更新单元格 |
| `add_row` | sheet, data[], after_row | 在指定行后插入一行 |
| `add_column` | sheet, header, default_value | 在末尾添加新列 |
| `rename_sheet` | old, new | 重命名工作表 |
| `add_sheet` | name | 添加新工作表 |
| `set_cell_style` | sheet, row, col, bold, color | 设置单元格样式 |
| `delete_row` | sheet, row | 删除指定行 |

---

## 自动排版规范

### Word 文档排版

| 元素 | 规范 |
|------|------|
| 页边距 | 上/下 2.54cm, 左 3.17cm, 右 3.17cm (A4 标准) |
| 正文字体 | Calibri 10.5pt, 深灰 #333333 |
| 一级标题 | Calibri 16pt, 深蓝 #1B3A5C, 粗体 |
| 二级标题 | Calibri 13pt, 深蓝 #1B3A5C |
| 行距 | 1.15 倍 |
| 表格表头 | 9.5pt Calibri, 蓝色背景 #2E6BA4, 白色字, 加粗居中 |
| 表格数据 | 9.5pt Calibri, 灰色边框, 隔行交替 #F2F6FA |
| 页码 | 页脚居中, 8pt 灰色 |
| 封面 | 标题 26pt 居中, 副标题 14pt, 作者 10pt |

### Excel 工作簿排版

| 元素 | 规范 |
|------|------|
| 表头 | 白色粗体 Calibri 10pt, 深蓝背景 #2E6BA4, 居中 |
| 数据 | 深灰 Calibri 10pt #333333, 左对齐 |
| 隔行交替 | 偶数行浅蓝背景 #F2F6FA |
| 边框 | 细线灰色 #BBBBBB 全边框 |
| 表头底线 | 中粗深蓝 #2E6BA4 |
| 冻结窗格 | 可配置（推荐冻结首行）|
| 打印设置 | 横向, 自适应宽度 |
| Excel 表格 | 自动添加（支持筛选和样式）|

---

## 安全注意事项

1. **脚本从 stdin 读取 JSON 输入** — JSON 由 `json.loads` 解析，不会执行任意代码。但输入中不应包含用户不可信的原始内容。
2. **文件写入** — 所有脚本仅在指定的输出路径写入文件。不会覆盖系统文件。确保输出路径可写。
3. **外部依赖** — `python-docx` 和 `openpyxl` 是成熟的库，但如有敏感文档建议在隔离环境中使用。
4. **路径安全** — 输出路径由脚本参数指定，不拼接用户输入构造路径，无路径穿越风险。

## 常见错误与处理

1. **python-docx / openpyxl 未安装**
   ```bash
   pip install python-docx openpyxl
   ```

2. **输入 JSON 格式错误**
   - 确保 JSON 是合法的，用 `python -m json.tool` 验证
   - 字段名必须和参考文档中完全一致

3. **编辑已有文档时文字找不到**
   - `replace_text` 区分大小写
   - 如果文档中有分节、文本框中的文字，需改为手动查找方式

4. **Excel 表头找不到**
   - `update_cell_by_header` 仅在首行查找精确匹配
   - 表头名区分大小写

5. **输出路径权限**
   - 确保输出目录可写，使用绝对路径

## 验证检查清单

- [ ] 生成的 .docx / .xlsx 文件已保存到指定路径
- [ ] 用 `python -m markitdown output.docx` 提取文字验证内容完整
- [ ] Word 文档标题、章节、表格、段落均已正确渲染
- [ ] Excel 工作簿多 sheet、表头/数据/汇总行均正确
- [ ] 排版规范已应用（间距、颜色、字体、边框）
- [ ] 文档的页边距和页码符合 Office 标准
