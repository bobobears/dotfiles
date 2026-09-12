# .doc 往返 + 公文表格手术：完整可复现配方

来源会话：2026-09-02，填写《医疗机构传染病防治分类监督综合评价自查评价表》征求意见汇总表（.doc 输入 → .doc/.docx 双格式交付）。

## 1. 往返转换

```bash
cp "附件.doc" work/src.doc
soffice --headless --convert-to docx src.doc --outdir work/   # MS Word 2007 XML filter
# ... python-docx 编辑 ...
soffice --headless --convert-to doc out.docx --outdir work/   # MS Word 97 filter
```

验证：`soffice --headless --convert-to docx final.doc --outdir verify/` 后重读，确认改动仍在。

## 2. 给复杂表格加行（保留边框/列宽）

```python
import copy, docx
d = docx.Document('src.docx')
t0 = d.tables[0]                      # 汇总表：row0=表头，row1..N=空数据行
empty_tr = t0.rows[1]._tr             # 取一个现有空行的 XML
for _ in range(4):                    # 补足到需要的行数
    t0._tbl.append(copy.deepcopy(empty_tr))
```

不要用 `t0.add_row()` —— 会丢掉原表的 tcBorders/tcW。

## 3. 填单元格（中文文档必须设 eastAsia 字体）

```python
from docx.shared import Pt
from docx.oxml.ns import qn

def set_cell(cell, text):
    for p in cell.paragraphs[1:]:     # 清掉多余段落，保留第一个
        p._p.getparent().remove(p._p)
    r = cell.paragraphs[0].add_run(text)
    r.font.name = '宋体'
    r.font.size = Pt(10.5)
    r._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')   # 关键！
```

## 4. 合并单元格去重（编辑 run 前必做）

```python
def cell_unique_tcs(row):
    seen, out = set(), []
    for c in row.cells:
        if id(c._tc) not in seen:     # 横向合并格在每个跨越列都返回同一 _tc
            seen.add(id(c._tc)); out.append(c._tc)
    return out
```

## 5. 删除特定 run（编辑残留 / 划掉文字）

```python
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
for tc in cell_unique_tcs(row):
    for r in list(tc.iter(f'{{{W}}}r')):
        t = ''.join(x.text or '' for x in r.findall(f'{{{W}}}t'))
        if '删句号' in t:              # 按文本内容匹配，不要依赖 strike 标志
            r.getparent().remove(r)
```

注意：LibreOffice 转换后删除线常挂在 `w:rStyle`（字符样式）上而非显式 `<w:strike/>`，
所以 `r.font.strike` 可能为 None —— 按文本匹配最可靠。

## 6. 机构名称推断 → 一次确认

公文需要单位全称时：先搜本地库（HRMS employees、患者花名册等）找候选名，
再用 clarify 问一个问题、把推断出的名字作为推荐项。不要空手问用户"你们单位叫什么"。
