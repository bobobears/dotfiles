# Excel 工作簿 JSON 结构参考

## 创建工作簿结构 (`create_excel.py`)

```json
{
  "title": "报告标题",
  "sheets": [
    {
      "name": "Sheet1",
      "freeze_pane": "A2",
      "column_widths": [12, 20, 15, 15],
      "title_cell": {
        "row": 1, "col": 1,
        "text": "报告标题",
        "merge_to": {"row": 1, "col": 4}
      },
      "tables": [
        {
          "headers": ["列A", "列B", "列C"],
          "rows": [
            ["数据1", "数据2", "数据3"]
          ],
          "start_row": 2
        }
      ],
      "summary_rows": [
        {"row_type": "after_table", "text": "合计:", "bold": true}
      ]
    }
  ]
}
```

### 字段说明

| 字段 | 说明 |
|------|------|
| `freeze_pane` | 冻结窗格位置，如 "A2" 冻结首行 |
| `column_widths` | 每列宽度（字符数），不指定则自动适配 |
| `title_cell` | 合并单元格标题行（可选） |
| `tables[].start_row` | 表格起始行号（默认 1）|
| `summary_rows` | 表格下方的汇总/合计行 |

## 编辑工作簿结构 (`edit_excel.py`)

```json
{
  "changes": [
    {"action": "update_cell", "sheet": "Sheet1", "row": 2, "col": 1, "value": "新值"},
    {"action": "update_cell_by_header", "sheet": "Sheet1", "header": "姓名", "row": 3, "value": "张三"},
    {"action": "add_row", "sheet": "Sheet1", "data": ["A","B","C"], "after_row": 5},
    {"action": "add_column", "sheet": "Sheet1", "header": "新列", "default_value": ""},
    {"action": "rename_sheet", "old": "Sheet1", "new": "数据"},
    {"action": "add_sheet", "name": "汇总"},
    {"action": "delete_row", "sheet": "Sheet1", "row": 3}
  ]
}
```

## 自动应用的排版规范

- **表头**: 白色粗体 Calibri 10pt, 深蓝背景 (#2E6BA4), 居中
- **数据**: 深灰 Calibri 10pt (#333333), 左对齐
- **隔行交替**: 偶数行浅蓝背景 (#F2F6FA)
- **边框**: 细线灰色 (#BBBBBB) 全边框
- **表头底部**: 中粗深蓝横线 (#2E6BA4)
- **页设置**: 横向, 自适应宽度
- **工作表表格**: 自动添加 Excel 表格（支持筛选）
- **冻结**: 可配置冻结窗格
