#!/usr/bin/env python3
"""把 smd.db 在册数据填进老格式 .xls 模板（xlrd 读 + xlwt 写，逐格保样式）。

用法: uv run --with xlrd==1.2.0 --with xlwt python fill_xls_template.py <模板.xls> <输出.xls>

适用：20 列《在册基本信息.xls》类模板（前 3 行表头含合并区，数据从第 4 行起，
列序与 patients 表字段一一对应）。其他 20 列同构模板可直接复用；列不同的模板改 COLS。
"""
import sqlite3
import sys
import xlrd
import xlwt

SRC = sys.argv[1]
OUT = sys.argv[2]
DB = "/home/bobobears/smd_db/smd.db"

# 列顺序必须与模板表头一致（模板第 3 行 index=2 是列名行）
COLS = [
    "seq_no", "name", "id_card", "guardian_name", "phone",
    "hukou_addr", "cur_addr", "diagnosis", "risk_level", "color_status",
    "guardianship", "color_type", "dual_supervision", "four_party", "town",
    "institution", "out_area_addr", "platform_transfer", "has_cert", "remark",
]
TEXT_COLS = {"id_card", "phone"}  # 强制文本，防 float 精度丢失

book = xlrd.open_workbook(SRC, formatting_info=True)
sh = book.sheet_by_index(0)
assert sh.ncols == len(COLS), f"模板列数 {sh.ncols} != 期望 {len(COLS)}，请改 COLS 后重跑"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
rows = [dict(r) for r in conn.execute(
    "SELECT * FROM patients WHERE status='在册' ORDER BY seq_no")]
print(f"在册人数: {len(rows)}")

wb = xlwt.Workbook(encoding="utf-8")
ws = wb.add_sheet(sh.name or "Sheet1")

# ---- 列宽 / 行高（BIFF: 宽=1/256字符, 高=1/20磅，原样照抄不换算）----
for c in range(sh.ncols):
    info = sh.colinfo_map.get(c)
    if info is not None and info.width:
        ws.col(c).width = int(info.width)
base_row = None
for r in range(sh.nrows - 1, 2, -1):
    if r in sh.rowinfo_map:
        base_row = r
        break
base_h = sh.rowinfo_map[base_row].height if base_row in sh.rowinfo_map else 255 * 20

def style_from_xf(r, c):
    """xlrd xf 索引 → xlwt XFStyle（字体/对齐/填充/边框）"""
    xf = book.xf_list[sh.cell_xf_index(r, c)]
    f = book.font_list[xf.font_index]
    bg = xf.background
    bd = xf.border
    al = xf.alignment
    style = xlwt.XFStyle()
    style.font.name = f.name or "宋体"
    style.font.height = max(int(f.height), 110)  # 防 0 值异常
    style.font.bold = bool(f.bold)
    if f.colour_index is not None and f.colour_index != 32767:  # 32767=自动色
        style.font.colour_index = f.colour_index
    if bg.fill_pattern == 1:
        from xlwt import Pattern as P
        style.pattern.pattern = P.SOLID_PATTERN
        style.pattern.pattern_fore_colour = bg.pattern_colour_index
    def bs(s):
        return {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7}.get(int(s or 0), 0)
    style.borders.top = bs(bd.top_line_style)
    style.borders.bottom = bs(bd.bottom_line_style)
    style.borders.left = bs(bd.left_line_style)
    style.borders.right = bs(bd.right_line_style)
    from xlwt import Alignment as A
    ha = {0: A.HORZ_GENERAL, 1: A.HORZ_LEFT, 2: A.HORZ_CENTER,
          3: A.HORZ_RIGHT, 4: A.HORZ_FILLED, 5: A.HORZ_JUSTIFIED}
    va = {0: A.VERT_TOP, 1: A.VERT_CENTER, 2: A.VERT_BOTTOM}
    style.alignment.horz = ha.get(int(al.hor_align), A.HORZ_GENERAL)
    style.alignment.vert = va.get(int(al.vert_align), A.VERT_CENTER)
    style.alignment.wrap = int(al.text_wrapped) or 0
    return style

def display_value(field, v):
    """DB 值 → 对外展示值（空值一律留空，不臆造）"""
    if v is None:
        return ""
    if field in ("seq_no", "risk_level"):
        try:
            return int(v)
        except (TypeError, ValueError):
            return str(v).strip()
    if field in ("dual_supervision", "four_party", "platform_transfer"):
        return {1: "是", 0: "否"}.get(int(v), "")
    if field == "has_cert":
        # 0=无 写"无"；NULL/1（有/未标注）留空，不替用户表态
        return {0: "无"}.get(int(v), "")
    s = str(v).strip()
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]  # 去 sqlite 整数的 .0 尾巴
    return s

n_out = max(sh.nrows, 3 + len(rows))  # 数据超模板行数时扩行，不静默丢行
for r in range(n_out):
    if r in sh.rowinfo_map and sh.rowinfo_map[r].height:
        ws.row(r).height = int(sh.rowinfo_map[r].height)
    elif r >= 3:
        ws.row(r).height = int(base_h)
    for c in range(sh.ncols):
        src_r = min(r, sh.nrows - 1)  # 超出模板的行沿用最后一行样式
        st = style_from_xf(src_r, c)
        if r < sh.nrows:
            v = sh.cell_value(r, c)
            sv = str(v).strip()
            if r in (0, 1, 2) and sv:  # 表头行原样保留
                ws.write(r, c, v, st)
        if r >= 3:
            i = r - 3
            if i < len(rows):
                field = COLS[c]
                if field == "seq_no":
                    val = i + 1  # 呈现序号：在册顺序从 1 重编
                else:
                    val = display_value(field, rows[i].get(field))
                if val != "":
                    if field in TEXT_COLS:
                        ws.write(r, c, str(val), st)
                    else:
                        ws.write(r, c, val, st)
            else:
                ws.write(r, c, "", st)

# 合并标题行：合并区内所有格已写好样式，直接标记合并区
# （xlwt 无 write_merge；sh.merged_cells 的 rhi/chi 是开区间上界，要 -1）
for rlo, rhi, clo, chi in sh.merged_cells:
    ws.merge(rlo, rhi - 1, clo, chi - 1)

wb.save(OUT)
print(f"已保存: {OUT} ({n_out} 行)")

# ---- 读回验证 ----
chk = xlrd.open_workbook(OUT, formatting_info=True)
ch = chk.sheet_by_index(0)
names = sum(1 for r in range(3, ch.nrows) if str(ch.cell_value(r, 1)).strip())
bad_type = [ (r, ch.cell_type(r, c)) for r in range(3, min(ch.nrows, 3+len(rows)))
             for c in (2, 4) if ch.cell_value(r, c) != "" and ch.cell_type(r, c) != 1 ]
assert names == len(rows), f"姓名行数 {names} != 在册数 {len(rows)}"
assert not bad_type, f"身份证/电话有非文本格: {bad_type[:5]}"
assert len(ch.merged_cells) == len(sh.merged_cells), "合并区数量与模板不一致"
print(f"验证通过: {names} 人, 身份证/电话均为文本, 合并区 {len(ch.merged_cells)} 处")
