#!/usr/bin/env python3
"""月公卫工作量统计表模板（2026-10 样式基准）

用法：python3 月公卫工作量统计表模板.py [YYYY] [M]
默认取当前日期；输出到 ~/private_db/knowledge/medical/工作量统计/YYYY年M月公卫工作量统计表.xlsx

结构（2026年9月/10月实际文件样式）：
  R1  标题「月项目公卫工作量统计表」Arial 14b，A1:G1 合并，蓝底 FFBDD7EE
  R2  副题「统计月份：YYYY年M月」宋体 11，A2:G2 合并
  R3  表头：序号/时间/姓名/档案录入（份）/电话访视（次）/上门访视（次）/其他，Arial 11b，蓝底 FFD9EAF7，四边细边框
  R4+ 数据行 21 行，序号预填，四边细边框，日期列 datetime + m"月"d"日" 格式
  列宽 A6 B12 C13 D16 E13 F13 G18；行高 R1=30 R2=20 R3=36 数据行=22
"""
import os, sys
from datetime import datetime

try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
except ImportError:
    print('缺少 openpyxl，请用 venv 解释器：~/.hermes/hermes-agent/venv/bin/python')
    sys.exit(1)

now = datetime.now()
year = int(sys.argv[1]) if len(sys.argv) > 1 else now.year
month = int(sys.argv[2]) if len(sys.argv) > 2 else now.month

out = os.path.expanduser(f'~/private_db/knowledge/medical/工作量统计/{year}年{month}月公卫工作量统计表.xlsx')
os.makedirs(os.path.dirname(out), exist_ok=True)
if os.path.exists(out):
    print(f'已存在，跳过：{out}')
    sys.exit(0)

wb = openpyxl.Workbook()
ws = wb.active
ws.title = f'{month}月公卫工作量'

thin = Side(style='thin')
border_all = Border(top=thin, bottom=thin, left=thin, right=thin)
align_c = Alignment(horizontal='center', vertical='center')
fill_title = PatternFill('solid', fgColor='FFBDD7EE')
fill_head = PatternFill('solid', fgColor='FFD9EAF7')
font_title = Font(name='Arial', size=14, bold=True)
font_sub = Font(name='宋体', size=11)
font_head = Font(name='Arial', size=11, bold=True)
font_data = Font(name='Arial', size=11)
font_data_cn = Font(name='宋体', size=11)

for col, w in {'A': 6, 'B': 12, 'C': 13, 'D': 16, 'E': 13, 'F': 13, 'G': 18}.items():
    ws.column_dimensions[col].width = w
ws.row_dimensions[1].height = 30
ws.row_dimensions[2].height = 20
ws.row_dimensions[3].height = 36
for r in range(4, 25):
    ws.row_dimensions[r].height = 22

ws.merge_cells('A1:G1')
c = ws.cell(1, 1, '月项目公卫工作量统计表')
c.font, c.alignment, c.fill = font_title, align_c, fill_title
for i in range(1, 8):
    ws.cell(1, i).fill = fill_title

ws.merge_cells('A2:G2')
c = ws.cell(2, 1, f'统计月份：{year}年{month}月')
c.font, c.alignment = font_sub, align_c

headers = ['序号', '时间', '姓名', '档案录入（份）', '电话访视（次）', '上门访视（次）', '其他']
for i, h in enumerate(headers, 1):
    c = ws.cell(3, i, h)
    c.font, c.alignment, c.fill, c.border = font_head, align_c, fill_head, border_all

for seq in range(1, 22):
    r = 3 + seq
    c = ws.cell(r, 1, seq)
    c.font, c.alignment, c.border = font_data, align_c, border_all
    for col in range(2, 8):
        ws.cell(r, col).border = border_all

wb.save(out)
print(f'已创建：{out}')
