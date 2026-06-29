# Word 文档 JSON 结构参考

## 创建文档结构 (`create_word.py`)

```json
{
  "title": "文档标题",
  "subtitle": "副标题（可选）",
  "author": "作者名（可选）",
  "sections": [
    {
      "heading": "章节标题",
      "level": 1,
      "paragraphs": [
        {"text": "普通段落文字", "style": "normal"},
        {"text": "粗体引导文字", "bold": true, "text_after": "后面继续普通文字"},
        {"text": "项目符号项", "style": "bullet"},
        {"text": "编号项", "style": "numbered"},
        {"text": "引用文字", "style": "quote"}
      ],
      "tables": [
        {
          "headers": ["列1", "列2", "列3"],
          "rows": [
            ["数据1", "数据2", "数据3"]
          ],
          "caption": "表格标题（可选）"
        }
      ]
    }
  ]
}
```

### 段落的 style 选项

| style | 效果 |
|-------|------|
| `normal` (默认) | 普通正文段落 |
| `bullet` | 项目符号列表 |
| `numbered` | 编号列表 |
| `quote` | 引用样式（斜体、灰色） |

### 章节 level 选项

| level | 样式 | 字号 |
|-------|------|------|
| 1 | Heading 1 | 16pt, 深蓝 |
| 2 | Heading 2 | 13pt, 深蓝 |
| 3 | Heading 3 | 11pt, 深蓝 |

## 编辑文档结构 (`edit_word.py`)

```json
{
  "changes": [
    {"action": "replace_text", "old": "旧文字", "new": "新文字"},
    {"action": "add_paragraph", "text": "新段落", "after_heading": "章节标题"},
    {"action": "add_table", "headers": ["A","B"], "rows": [["1","2"]], "after_heading": "..."},
    {"action": "set_title", "text": "新文档标题"},
    {"action": "change_heading", "old": "旧标题", "new": "新标题"}
  ]
}
```

## 自动应用的排版规范

- **页边距**: 上/下 2.54cm, 左 3.17cm, 右 3.17cm（A4 标准）
- **正文字体**: Calibri 10.5pt, 深灰色 (#333333)
- **标题字体**: Calibri, 深蓝 (#1B3A5C)
- **行距**: 1.15 倍
- **表格**: 9.5pt Calibri, 蓝色表头行 (#2E6BA4), 白色字, 隔行交替浅蓝背景 (#F2F6FA)
- **页码**: 页脚居中, 8pt 灰色
- **列表**: 自动缩进的 List Bullet / List Number 样式
