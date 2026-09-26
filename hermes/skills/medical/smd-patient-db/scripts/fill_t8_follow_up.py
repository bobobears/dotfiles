# -*- coding: utf-8 -*-
"""表8 随访服务记录表生成 v6（鲁绪霖 2026-09-21）
v6 相对 v5 的两处修正（依金医生反馈）：
  1) 目前症状行"12"：方框串 jc 由 distribute 改 left（否则按每字一格拉开成扁长框），
     并用空格把整串方框拉回原长度
  2) 康复措施行"4"填错框：改为先取全部方框再按序号填；并排多方框的行改用半角数字
v5 相对 v4：填写字号 6pt + 行距 exact（方框不再压上下行线）
v4 相对 v3 的三处修正（依金医生反馈）：
  1) 编号移到表头行右侧：改为右对齐制表位（w:tabs right @7917 twips = 表格右框内13mm），不再用空格排版
  2) 填写数字=【数字 + 细边框】：单格答案用全角，并排多方框的行用半角，方框大小与原表格 □ 一致（原用半角数字，框形偏窄长）
  3) 用药指导行的"药物1："补填药物品名
"""
import copy
import docx
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

TPL = '/home/bobobears/下载/精神障碍管理/16、附件1-2严重精神障碍管理治疗工作用表.docx'
OUT = '/home/bobobears/下载/精神障碍管理/2026.9/随访记录/随访服务记录表-鲁绪霖-20260921.docx'

NAME = '鲁绪霖'
RECORD_NO = '201－03456'
FOLLOW_DATE = ('2026', '9', '21')
NEXT_DATE = ('2026', '12', '21')

FORM_TYPE = '2'
TARGET = '2'
RISK = '0'
SYMPTOM = '12'
SYMPTOM_OTHER_TEXT = '无'
INSIGHT = '2'
SLEEP = '2'
DIET = '2'
SOCIAL = ['2', '2', '9', '2', '2']
DANGER = '7'
LOCK = '1'
HOSPITAL = '0'
LAB = '1'
ADHERENCE = '1'
ADVERSE = '1'
EFFECT = '3'
REFERRAL = ['1', '1']
REHAB = ['1', '4']
CATEGORY = '3'
DRUG_NAME = '舒必利片100mg'          # 用药情况行：药物名+规格
DRUG_NAME_GUIDE = '舒必利片100mg'    # 用药指导行：药物品名
DRUG_DOSE = '100'
DOSAGE = ('0', '0', '100')
FILL_SIZE = '12'      # 填写数字字号（半磅）= 6pt

XMLSPACE = '{http://www.w3.org/XML/1998/namespace}space'
RPR_ORDER = ['rStyle', 'rFonts', 'b', 'bCs', 'i', 'iCs', 'caps', 'smallCaps', 'strike',
             'dstrike', 'outline', 'shadow', 'emboss', 'imprint', 'noProof', 'snapToGrid',
             'vanish', 'webHidden', 'color', 'spacing', 'w', 'kern', 'position', 'sz', 'szCs',
             'highlight', 'u', 'effect', 'bdr', 'shd', 'fitText', 'vertAlign', 'rtl', 'cs',
             'em', 'lang', 'eastAsianLayout', 'specVanish', 'oMath']
TCPR_ORDER = ['cnfStyle', 'tcW', 'gridSpan', 'hMerge', 'vMerge', 'tcBorders', 'shd',
              'noWrap', 'tcMar', 'textDirection', 'tcFitText', 'vAlign', 'hideMark']
PPR_ORDER = ['pStyle', 'keepNext', 'keepLines', 'pageBreakBefore', 'framePr', 'widowControl',
             'numPr', 'suppressLineNumbers', 'pBdr', 'shd', 'tabs', 'suppressAutoHyphens',
             'kinsoku', 'wordWrap', 'overflowPunct', 'topLinePunct', 'autoSpaceDE',
             'autoSpaceDN', 'bidi', 'adjustRightInd', 'snapToGrid', 'spacing', 'ind',
             'contextualSpacing', 'mirrorIndents', 'suppressOverlap', 'jc', 'textDirection',
             'textAlignment', 'textboxTightWrap', 'outlineLvl', 'divId', 'cnfStyle', 'rPr',
             'sectPr', 'pPrChange']
HW2FW = str.maketrans('0123456789-', '０１２３４５６７８９－')


def fw(s):
    return s.translate(HW2FW)


def insert_ordered(parent, el, order):
    tag = el.tag.split('}')[1]
    idx = order.index(tag)
    for child in parent:
        ct = child.tag.split('}')[1]
        if ct in order and order.index(ct) > idx:
            child.addprevious(el)
            return
    parent.append(el)


def tc_of(x):
    return x._tc if hasattr(x, '_tc') else x


def paras(x):
    el = tc_of(x)
    if el.tag == qn('w:p'):
        return [el]
    return el.findall(qn('w:p'))


def txt_of(r):
    return ''.join(n.text or '' for n in r.iter(qn('w:t')))


def box_pairs(x):
    out = []
    for p in paras(x):
        for r in p.findall(qn('w:r')):
            if '□' in txt_of(r):
                out.append((r, p))
    return out


def set_run_text(r_el, text):
    ts = r_el.findall(qn('w:t'))
    if not ts:
        t = OxmlElement('w:t')
        r_el.append(t)
        ts = [t]
    ts[0].text = text
    ts[0].set(XMLSPACE, 'preserve')
    for extra in ts[1:]:
        r_el.remove(extra)


def add_bdr(rPr):
    for old in rPr.findall(qn('w:bdr')):
        rPr.remove(old)
    bdr = OxmlElement('w:bdr')
    bdr.set(qn('w:val'), 'single')
    bdr.set(qn('w:sz'), '4')
    bdr.set(qn('w:space'), '0')
    bdr.set(qn('w:color'), 'auto')
    insert_ordered(rPr, bdr, RPR_ORDER)


def set_size(rPr, half_points):
    """设定字号（半磅）。填写数字比正文小一号(9pt)，方框才不会顶到上下行线。"""
    for tag in ('w:sz', 'w:szCs'):
        el = rPr.find(qn(tag))
        if el is None:
            el = OxmlElement(tag)
            insert_ordered(rPr, el, RPR_ORDER)
        el.set(qn('w:val'), half_points)


def set_jc(p_el, val='left'):
    """段落水平对齐。jc=distribute 会把每个字按"一格"拉开，run 边框跟着被拉开，
    多位数字（如 12）就被撑成很宽的扁长框；改成 left 后框宽=自身字宽。"""
    pPr = p_el.find(qn('w:pPr'))
    if pPr is None:
        pPr = OxmlElement('w:pPr')
        p_el.insert(0, pPr)
    jc = pPr.find(qn('w:jc'))
    if jc is None:
        jc = OxmlElement('w:jc')
        insert_ordered(pPr, jc, PPR_ORDER)
    jc.set(qn('w:val'), val)


def box_run(r_el, digit, fullwidth=True):
    """把 run 写成【数字 + 细边框】——方框大小与原表格 □ 一致。
    fullwidth=False 用半角数字：宽度约为全角一半，配合边框内边距后
    效果方框 ≈ 10.2pt ≈ 印刷 □（10.5pt），用于 康复措施 / 目前症状 这种
    同一行并排多个方框、框距要与原表一致的场合；单独的右侧答案格用全角。"""
    set_run_text(r_el, (fw(digit) if fullwidth else digit + ' '))
    rPr = r_el.find(qn('w:rPr'))
    if rPr is None:
        rPr = OxmlElement('w:rPr')
        r_el.insert(0, rPr)
    set_size(rPr, FILL_SIZE)
    add_bdr(rPr)


def set_exact_line(p_el, twips='200'):
    """把段落行距设为固定值（默认 10pt）。行距用 atLeast 时，run 边框会被拉成整行高、压住上下行线；
    改成 exact 后边框只包住字身，方框明显变小。"""
    pPr = p_el.find(qn('w:pPr'))
    if pPr is None:
        pPr = OxmlElement('w:pPr')
        p_el.insert(0, pPr)
    sp = pPr.find(qn('w:spacing'))
    if sp is None:
        sp = OxmlElement('w:spacing')
        insert_ordered(pPr, sp, PPR_ORDER)
    sp.set(qn('w:line'), twips)
    sp.set(qn('w:lineRule'), 'exact')


def set_exact_rule(p_el, fallback='240'):
    """把段落行距规则由 atLeast 改成 exact（保留原 line 值）。含正文的段落也适用，
    这样方框只包住 9pt 字身，不再被拉高到行线。"""
    pPr = p_el.find(qn('w:pPr'))
    if pPr is None:
        pPr = OxmlElement('w:pPr')
        p_el.insert(0, pPr)
    sp = pPr.find(qn('w:spacing'))
    if sp is None:
        sp = OxmlElement('w:spacing')
        insert_ordered(pPr, sp, PPR_ORDER)
        sp.set(qn('w:line'), fallback)
    sp.set(qn('w:lineRule'), 'exact')


def fill_pair(pair, text, fullwidth=True):
    r_el, p_el = pair
    box_run(r_el, text, fullwidth=fullwidth)
    # 段落里除方框外还有正文 → 只把行距规则改 exact（保住正文行高）
    other = ''.join(txt_of(r) for r in p_el.findall(qn('w:r')) if r is not r_el)
    other = other.replace('□', '').replace('/', '').replace('\u2009', '').strip()
    if other:
        set_exact_rule(p_el)
    else:
        set_exact_line(p_el)


def fill_box_in(x, text, which=0, fullwidth=True):
    pairs = box_pairs(x)
    if len(pairs) <= which:
        raise RuntimeError('找不到第%d个方框: %s' % (which, text))
    fill_pair(pairs[which], text, fullwidth=fullwidth)


def add_copy_run(paragraph, base_r_el, text, boxed=True):
    r = paragraph.add_run(fw(text) if boxed else text)
    if base_r_el is not None:
        base_rPr = base_r_el.find(qn('w:rPr'))
        if base_rPr is not None:
            existing = r._element.find(qn('w:rPr'))
            if existing is not None:
                r._element.remove(existing)
            r._element.insert(0, copy.deepcopy(base_rPr))
    if boxed:
        rPr = r._element.find(qn('w:rPr'))
        set_size(rPr, FILL_SIZE)
        add_bdr(rPr)
    return r


# ---------- 打开模板，只保留表8相关元素 ----------
doc = docx.Document(TPL)
body = doc.element.body
kids = list(body)
KEEP = {111, 112, 113, 114}
sect_idx = len(kids) - 1
for i, k in enumerate(kids):
    if i in KEEP or i == sect_idx:
        continue
    body.remove(k)
# 表8 所属节的页面边距（模板里由"表8 之后最近的 sectPr"定义 = 1797/1797/1361/1361）。
# 若沿用 body 末尾 sectPr（1134/1418），表格右竖线会比下方注释文字窄 76px，
# 金医生反馈的"表格右边距过大、与下边文字不对齐"即此。渲染验收：表格左/右竖线 x=168/1077@150dpi。
sect = body.find(qn('w:sectPr'))
pgsz = sect.find(qn('w:pgSz'))
if pgsz is not None:
    pgsz.set(qn('w:w'), '11906'); pgsz.set(qn('w:h'), '16838')
mar = sect.find(qn('w:pgMar'))
if mar is not None:
    for _k, _v in (('top', '1361'), ('right', '1797'), ('bottom', '1361'), ('left', '1797')):
        mar.set(qn('w:' + _k), _v)

tbl_el = [k for k in body if k.tag == qn('w:tbl')][0]
import docx.table
T = docx.table.Table(tbl_el, doc)


def cells_of(ri):
    return T.rows[ri]._tr.findall(qn('w:tc'))


# ---------- 表头：姓名 + 编号（制表位右对齐） ----------
name_p_el = [k for k in body if k.tag == qn('w:p')
             and '姓名' in ''.join(n.text or '' for n in k.iter(qn('w:t')))][0]
NP = docx.text.paragraph.Paragraph(name_p_el, doc)

# 1) 加右对齐制表位：pos=7917twips → 编号右端落在表格右框内约 13mm（与样表一致）
pPr = name_p_el.find(qn('w:pPr'))
tabs = OxmlElement('w:tabs')
tab = OxmlElement('w:tab')
tab.set(qn('w:val'), 'right')
tab.set(qn('w:pos'), '7917')
tabs.append(tab)
insert_ordered(pPr, tabs, PPR_ORDER)

runs_el = name_p_el.findall(qn('w:r'))
# 2) 姓名填入第一个空白 run（保留下划线）
for r in runs_el:
    tx = txt_of(r)
    if tx and '姓名' not in tx and '编号' not in tx and tx.strip() == '':
        set_run_text(r, NAME)
        break
# 3) 把 36 空格 run 换成制表符
for r in runs_el:
    tx = txt_of(r)
    if tx and tx.strip() == '' and '姓名' not in tx:
        for ch in list(r):
            if ch.tag != qn('w:rPr'):
                r.remove(ch)
        r.append(OxmlElement('w:tab'))
        break
# 4) 编号：'编号' + 每个数字一个方框（数字间细空格防边框粘连）
num_r_el = [r for r in runs_el if '编号' in txt_of(r)][0]
set_run_text(num_r_el, '编号')
seq = list(RECORD_NO)
for i, ch in enumerate(seq):
    if i > 0 and seq[i - 1] != '－' and ch != '－':
        add_copy_run(NP, num_r_el, '\u2009', boxed=False)
    add_copy_run(NP, num_r_el, ch, boxed=(ch != '－'))


# ---------- 日期 ----------
def fill_date(ri, ymd):
    rs = T.rows[ri].cells[1].paragraphs[0].runs
    rs[0].text = ' ' + ymd[0]
    rs[2].text = ' ' + ymd[1] + ' '
    rs[4].text = ' ' + ymd[2]


fill_date(0, FOLLOW_DATE)
fill_date(32, NEXT_DATE)

# ---------- 本次随访形式：只保留最右一个方框，数字填在框内 ----------
p1 = paras(T.rows[1].cells[1])[0]
base_r = None
for r in p1.findall(qn('w:r')):
    if '□' in txt_of(r):
        base_r = r
        set_run_text(r, txt_of(r).replace('□', ''))
        break
add_copy_run(docx.text.paragraph.Paragraph(p1, doc), base_r, FORM_TYPE, boxed=True)
set_exact_rule(p1)   # 行距改固定，方框不被拉高

# ---------- 本次随访对象：数字写在对应序号的框内 ----------
fill_box_in(T.rows[2].cells[1], TARGET, which=int(TARGET) - 1)

# ---------- 单选题行 ----------
fill_box_in(cells_of(6)[2], RISK)
for ri, val in [(8, INSIGHT), (9, SLEEP), (10, DIET)]:
    fill_box_in(cells_of(ri)[2], val)
for i, val in enumerate(SOCIAL):
    fill_box_in(cells_of(11 + i)[3], val)
for ri, val in [(17, LOCK), (19, LAB), (20, ADHERENCE), (21, ADVERSE)]:
    fill_box_in(cells_of(ri)[2], val)
fill_box_in(cells_of(31)[2], CATEGORY)

# ---------- 目前症状：编号填第一个框，'其他'后下划线补文字 ----------
c7 = paras(T.rows[7].cells[1])
for r in c7[0].findall(qn('w:r')):
    rPr = r.find(qn('w:rPr'))
    if rPr is not None and rPr.find(qn('w:u')) is not None and txt_of(r).strip() == '':
        set_run_text(r, ' ' + SYMPTOM_OTHER_TEXT)
        break
fill_box_in(c7[1], SYMPTOM, which=0, fullwidth=False)
set_jc(c7[1], 'left')   # distribute 会把"12"两个字拉开成扁长框
# jc 改 left 后整串方框比原表短约 33pt：第2个 □ 起每个前面加一个半角空格（10×3.15pt）拉回原长
k = 0
for r in c7[1].findall(qn('w:r')):
    if txt_of(r) == '□':
        if k:
            set_run_text(r, ' □')
        k += 1

# ---------- 危险行为：7 写第一个框 ----------
fill_box_in(paras(T.rows[16].cells[1])[1], DANGER, which=0)


# ---------- 拆出右侧答案格 ----------
def split_answer_cell(ri, answers):
    tc1 = cells_of(ri)[1]
    pr = tc1.find(qn('w:tcPr'))
    pr.find(qn('w:tcW')).set(qn('w:w'), '6258')
    pr.find(qn('w:gridSpan')).set(qn('w:val'), '7')
    tb = pr.find(qn('w:tcBorders'))
    if tb is None:
        tb = OxmlElement('w:tcBorders')
        insert_ordered(pr, tb, TCPR_ORDER)
    r_el = OxmlElement('w:right')
    r_el.set(qn('w:val'), 'nil')
    tb.append(r_el)
    new_tc = copy.deepcopy(tc1)
    npr = new_tc.find(qn('w:tcPr'))
    npr.find(qn('w:tcW')).set(qn('w:w'), '875')
    npr.remove(npr.find(qn('w:gridSpan')))
    ntb = npr.find(qn('w:tcBorders'))
    ntb.clear()
    for side, val in (('left', 'nil'), ('bottom', 'single')):
        el = OxmlElement('w:' + side)
        el.set(qn('w:val'), val)
        if val != 'nil':
            el.set(qn('w:sz'), '4')
            el.set(qn('w:space'), '0')
            el.set(qn('w:color'), 'auto')
        ntb.append(el)
    ps_new = new_tc.findall(qn('w:p'))
    for i, p in enumerate(ps_new):
        if i >= len(answers):
            new_tc.remove(p)
            continue
        for ch in list(p):
            if ch.tag != qn('w:pPr'):
                p.remove(ch)
    ps_orig = tc1.findall(qn('w:p'))
    ps_new = new_tc.findall(qn('w:p'))
    for i, val in enumerate(answers):
        pPr2 = ps_new[i].find(qn('w:pPr'))
        if pPr2 is not None:
            jc = pPr2.find(qn('w:jc'))
            if jc is None:
                jc = OxmlElement('w:jc')
                rPr_el = pPr2.find(qn('w:rPr'))
                if rPr_el is not None:
                    rPr_el.addprevious(jc)
                else:
                    pPr2.append(jc)
            jc.set(qn('w:val'), 'right')
        src_runs = ps_orig[i].findall(qn('w:r')) if i < len(ps_orig) else ps_orig[0].findall(qn('w:r'))
        src = src_runs[0] if src_runs else None
        new_r = copy.deepcopy(src) if src is not None else OxmlElement('w:r')
        for ch in list(new_r):
            if ch.tag != qn('w:rPr'):
                new_r.remove(ch)
        ps_new[i].append(new_r)
        box_run(new_r, val)
        set_exact_line(ps_new[i])
    tc1.addnext(new_tc)
    return tc1


def strip_boxes(tc):
    for p in tc.findall(qn('w:p')):
        for r in p.findall(qn('w:r')):
            for t_el in r.findall(qn('w:t')):
                if t_el.text and '□' in t_el.text:
                    t_el.text = t_el.text.replace('□', '')


strip_boxes(split_answer_cell(18, [HOSPITAL]))
strip_boxes(split_answer_cell(22, [EFFECT]))
strip_boxes(split_answer_cell(23, REFERRAL))

# ---------- 康复措施 ----------
# 必须一次性取出全部方框再逐个填：循环里重复 box_pairs() 时，已填过的方框不再是 □，
# 下一次的序号会整体错位（曾把"4"填进第 3 个框）。
pr30 = paras(T.rows[30].cells[1])[1]
pairs30 = box_pairs(pr30)
for i, val in enumerate(REHAB):
    fill_pair(pairs30[i], val, fullwidth=False)

# ---------- 用药情况：药物1 名称 + 剂量 ----------
tcs24 = cells_of(24)
p24 = tcs24[1].findall(qn('w:p'))[0]
add_copy_run(docx.text.paragraph.Paragraph(p24, doc),
             p24.findall(qn('w:r'))[-1], DRUG_NAME, boxed=False)
p24b = tcs24[2].findall(qn('w:p'))[0]
for r in p24b.findall(qn('w:r')):
    rPr = r.find(qn('w:rPr'))
    if rPr is not None and rPr.find(qn('w:u')) is not None and txt_of(r).strip() == '':
        set_run_text(r, ' ' + DRUG_DOSE + ' ')
        break

# ---------- 用药指导：药物1 品名 + 早中晚剂量 ----------
tcs27 = cells_of(27)
p27name = tcs27[1].findall(qn('w:p'))[0]
add_copy_run(docx.text.paragraph.Paragraph(p27name, doc),
             p27name.findall(qn('w:r'))[-1], DRUG_NAME_GUIDE, boxed=False)
p27 = tcs27[2].findall(qn('w:p'))[0]
k = 0
for r in p27.findall(qn('w:r')):
    rPr = r.find(qn('w:rPr'))
    if rPr is not None and rPr.find(qn('w:u')) is not None and k < len(DOSAGE):
        set_run_text(r, ' ' + DOSAGE[k] + ' ')
        k += 1

doc.save(OUT)
print('已保存:', OUT)
