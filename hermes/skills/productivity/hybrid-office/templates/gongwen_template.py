#!/usr/bin/env python3
"""党政机关公文（GB/T 9704）Word 生成骨架 —— 请示/报告/函/通知类红头公文

用法：uv run --with python-docx python gongwen.py
输出：docx。交付前用 python-docx 回读段落与表格验证内容完整。

格式基准（GB/T 9704-2012 常用简化版，适用于无红头版头的上报文）：
- 页面 A4；页边距 上3.7cm 下3.5cm 左2.8cm 右2.6cm
- 标题：二号(22pt) 方正小标宋简体（无该字体时回退宋体加粗）居中
- 主送机关：三号(16pt) 仿宋，顶格
- 正文：三号(16pt) 仿宋，首行缩进2字符，28磅固定行距，两端对齐
- 一级标题：黑体；二级标题：楷体；三级及以下：仿宋加粗
- 落款：单位+日期，右对齐（无版记时可省略签发人）
- 页码：页脚居中 “— n —”，四号半角宋体
"""
import docx
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

SONG, HEI, KAI, FS, XBS = "宋体", "黑体", "楷体", "仿宋", "方正小标宋简体"

# ===== 公文参数（按实际文种修改） =====
DOC_TITLE = "关于申请拨付2026年XX项目资金的报告"
TO_ORG = "XX区卫生健康委员会："
BODY = [  # (text, kind) kind: body=仿宋 / h1=黑体 / h2=楷体
    ("根据……（文号）精神，……（政策依据与名额分配）。", "body"),
    ("目前，我单位已……（项目进展，须与实际情况一致）。", "body"),
    ("为保障……，现申请拨付……，具体明细如下：", "body"),
]
TABLE_HEADERS = ["序号", "支出项目", "标准（元）", "金额（元）"]
TABLE_ROWS = [
    ["1", "工作生活补助", "20000", "20000"],
    ["2", "差旅费及各类保险", "按规定列支", "—"],
    ["合计", "", "", "20000"],
]
POST_TABLE = "我单位将严格遵守专项资金管理有关规定，确保专款专用，自觉接受监督检查。"
CLOSE = "妥否，请批示。"
SIGN_ORG = "XX单位（盖章）"
SIGN_DATE = "2026年  月  日"
OUT = "output.docx"

# ===== 生成 =====
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.top_margin, sec.bottom_margin = Cm(3.7), Cm(3.5)
sec.left_margin, sec.right_margin = Cm(2.8), Cm(2.6)

def set_font(run, name, size, bold=False):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)

def para(text="", font=FS, size=16, bold=False,
         align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=True, before=0, after=0, line=28):
    p = doc.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.space_before, pf.space_after = Pt(before), Pt(after)
    pf.line_spacing = Pt(line)
    if indent:
        pf.first_line_indent = Pt(size * 2)
    if text:
        set_font(p.add_run(text), font, size, bold)
    return p

# 标题（二号小标宋居中）
para(DOC_TITLE, XBS, 22, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, line=36, after=24)
# 主送机关（顶格）
para(TO_ORG, SONG, 16, align=WD_ALIGN_PARAGRAPH.LEFT, indent=False)
# 正文
for text, kind in BODY:
    if kind == "h1":
        para(text, HEI, 16)
    elif kind == "h2":
        para(text, KAI, 16)
    else:
        para(text, FS, 16)
# 资金/明细表（宋体，表头黑体加粗，合计行加粗）
table = doc.add_table(rows=len(TABLE_ROWS) + 1, cols=len(TABLE_HEADERS))
table.alignment = WD_TABLE_ALIGNMENT.CENTER
table.style = "Table Grid"
for j, h in enumerate(TABLE_HEADERS):
    c = table.cell(0, j); c.text = ""
    p = c.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(p.add_run(h), HEI, 14, bold=True)
for i, row in enumerate(TABLE_ROWS, start=1):
    bold = row[0] == "合计"
    for j, val in enumerate(row):
        c = table.cell(i, j); c.text = ""
        p = c.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_font(p.add_run(val), SONG, 14, bold=bold)
para(POST_TABLE, FS, 16, before=6)
para(CLOSE, FS, 16)
# 落款（右对齐）
para(SIGN_ORG, SONG, 16, align=WD_ALIGN_PARAGRAPH.RIGHT, indent=False, before=24)
para(SIGN_DATE, SONG, 16, align=WD_ALIGN_PARAGRAPH.RIGHT, indent=False)

doc.save(OUT)
print("SAVED", OUT)
