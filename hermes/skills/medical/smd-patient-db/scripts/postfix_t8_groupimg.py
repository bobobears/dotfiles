# -*- coding: utf-8 -*-
"""表8（随访服务记录）后处理：把"目前症状"与"康复措施"行的并排方框组换成整组图片。

为什么：run 边框（w:bdr）的内边距在 LibreOffice/WPS 里固定约 8.6pt，w:space=0 也压不下去，
带框数字最窄也有 33-38px，比印刷 □（23px）宽一大截；且 jc=distribute 会横向拉伸内嵌图片。
用一张按原模板 200dpi 像素复刻的 PNG 可把方框/斜线/数字做到与印刷完全一致。

用法: python3 postfix_t8_groupimg.py <docx路径>
（改文件前请先自行备份：cp <docx> <docx>.bak）
"""
import os
import sys

import docx
from docx.shared import Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.text.run import Run
from docx.text.paragraph import Paragraph
from PIL import Image, ImageDraw, ImageFont

# ---------- 几何参数（px@200dpi，实测自原始模板） ----------
DPI = 600
FONT = '/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc'
INK_W, INK_H = 8.3, 8.3        # 方框墨迹 ≈ 23x23px@200dpi（与印刷 □ 同尺寸）
STROKE = 4                     # 边框粗细(600dpi) ≈ 0.48pt
DIGIT_PT = 5.6                 # 框内数字字号
SLASH_DX = 5                   # 斜线右端距"下一个框"左端 5px@200
SLASH_W = 9                    # 斜线水平跨度
SLASH_OVER = 4                 # 斜线上下超出方框（模板实测约 4-6px，太长会顶到行线）
SYMPT_MARGIN_PX = 15           # 症状组图片内部左边距
SYMPT_LEFT_PX = [SYMPT_MARGIN_PX + v for v in (0, 103, 144, 185, 225, 266, 306, 347, 387, 428, 469, 509)]
SYMPT_W_PX = (1418 - 887) + SYMPT_MARGIN_PX + 6
REHAB_LEFT_PX = [0, 52, 92, 133, 174]
REHAB_W_PX = (1418 - 1222) + 6
REHAB_BLANK = 89               # "5其他"后填空线空格数（使方框组落到模板位置）


def px(pt):
    return int(round(pt * DPI / 72.0))


def make_group(lefts_px, width_px, fills, path):
    """生成"方框组"图片：方框 + 框间斜线 + 框内数字。fills: {框序号: '数字'}"""
    sx = DPI / 200.0
    W = int(round(width_px * sx))
    # 注意：SLASH_OVER 是 px@200，INK_H 是 pt —— 不能直接相加（曾算出 44px 画布、方框被裁）
    H = int(round(SLASH_OVER * sx)) * 2 + px(INK_H)
    img = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(img)
    iw, ih = px(INK_W), px(INK_H)
    y0 = int(round(SLASH_OVER * sx))
    f = ImageFont.truetype(FONT, px(DIGIT_PT))
    for i, lx in enumerate(lefts_px):
        x0 = int(round(lx * sx))
        if i > 0:                       # 斜线在本框左侧
            xr = x0 - int(round(SLASH_DX * sx))
            xl = xr - int(round(SLASH_W * sx))
            d.line([(xl, y0 - int(round(SLASH_OVER * sx))),
                    (xr, y0 + ih + int(round(SLASH_OVER * sx)))],
                   fill='black', width=max(2, int(round(1.2 * sx))))
        d.rectangle([x0, y0, x0 + iw - 1, y0 + ih - 1], outline='black', width=STROKE)
        if i in fills:
            t = fills[i]
            bb = d.textbbox((0, 0), t, font=f)
            d.text((x0 + (iw - (bb[2] - bb[0])) / 2.0 - bb[0],
                    y0 + (ih - (bb[3] - bb[1])) / 2.0 - bb[1]), t, font=f, fill='black')
    img.save(path)
    return W, H


def _is_group_run(r):
    """方框/斜线/旧带框数字 run"""
    t = ''.join(x.text or '' for x in r.findall(qn('w:t')))
    if any(c in t for c in '□/／'):
        return True
    rPr = r.find(qn('w:rPr'))
    return rPr is not None and rPr.find(qn('w:bdr')) is not None


def _put_image(doc, p, runs, png, w_pt, h_pt):
    anchor = runs[0]
    new_r = OxmlElement('w:r')
    anchor.addprevious(new_r)
    for r in runs:
        p.remove(r)
    Run(new_r, Paragraph(p, doc)).add_picture(png, width=Pt(w_pt), height=Pt(h_pt))


PPR_ORDER = ['pStyle', 'keepNext', 'keepLines', 'pageBreakBefore', 'framePr', 'widowControl',
             'numPr', 'suppressLineNumbers', 'pBdr', 'shd', 'tabs', 'suppressAutoHyphens',
             'kinsoku', 'wordWrap', 'overflowPunct', 'topLinePunct', 'autoSpaceDE', 'autoSpaceDN',
             'bidi', 'adjustRightInd', 'snapToGrid', 'spacing', 'ind', 'contextualSpacing',
             'mirrorIndents', 'suppressOverlap', 'jc', 'textDirection', 'textAlignment',
             'textboxTightWrap', 'outlineLvl', 'divId', 'cnfStyle', 'rPr', 'sectPr', 'pPrChange']


def set_ppr(pPr, tag, attrs):
    """按 OOXML 顺序写 pPr 子元素（ind 必须在 jc 之前、两者都在 rPr 之前）。"""
    el = pPr.find(qn('w:' + tag))
    if el is None:
        el = OxmlElement('w:' + tag)
        idx = PPR_ORDER.index(tag)
        ref = None
        for ch in pPr:
            nm = ch.tag.split('}')[-1]
            if nm in PPR_ORDER and PPR_ORDER.index(nm) > idx:
                ref = ch
                break
        if ref is not None:
            ref.addprevious(el)
        else:
            pPr.append(el)
    for k, v in attrs.items():
        el.set(qn(k if ':' in k else 'w:' + k), v)
    return el


def postfix(path, tmpdir=None):
    """把表8 的目前症状/康复措施方框组换成整组图片，原地写回。返回处理说明列表。"""
    tmpdir = tmpdir or os.environ.get('TMPDIR') or '/tmp'
    doc = docx.Document(path)
    T = doc.tables[0]
    done = []
    for tr in T.rows:
        head = ''.join(t.text or '' for t in tr._tr.iter(qn('w:t'))).strip()
        tcs = tr._tr.findall(qn('w:tc'))
        if len(tcs) < 2:
            continue
        if head.startswith('目前症状'):
            p = tcs[1].findall(qn('w:p'))[1]
            pPr = p.find(qn('w:pPr'))
            if pPr is not None:
                ind = pPr.find(qn('w:ind'))
                if ind is not None:          # 去掉首行缩进（改由图片内部补左边距）
                    for k in ('w:firstLine', 'w:firstLineChars', 'w:left', 'w:leftChars'):
                        if ind.get(qn(k)) is not None:
                            ind.attrib.pop(qn(k))
                # 方框组贴表格右侧：jc=right + 负右缩进（只 jc=right 仍差约 200 twips）
                set_ppr(pPr, 'jc', {'val': 'right'})
                set_ppr(pPr, 'ind', {'right': '-200'})
                sp = pPr.find(qn('w:spacing'))
                if sp is not None:           # 图高约 9.7pt，行高给 12pt
                    sp.set(qn('w:line'), '240')
                    sp.set(qn('w:lineRule'), 'exact')
            runs = [r for r in p.findall(qn('w:r'))]
            grp = [r for r in runs if _is_group_run(r)]
            if not grp:
                done.append('目前症状: 已是图片形式，跳过')
                continue
            png = os.path.join(tmpdir, 't8_group_sympt.png')
            W, H = make_group(SYMPT_LEFT_PX, SYMPT_W_PX, {0: '12'}, png)
            _put_image(doc, p, grp, png, W * 72.0 / DPI, H * 72.0 / DPI)
            done.append('目前症状: %d run -> 1 张方框组图 (%dx%dpx)' % (len(grp), W, H))
        elif head.startswith('康复措施'):
            p = tcs[1].findall(qn('w:p'))[1]
            pPr = p.find(qn('w:pPr'))
            if pPr is not None:
                # 方框组贴表格右侧：jc=right + 负右缩进（jc=left 会把图堆在左边）
                set_ppr(pPr, 'jc', {'val': 'right'})
                set_ppr(pPr, 'ind', {'right': '-200'})
            runs = [r for r in p.findall(qn('w:r'))]
            for r in runs:                            # 填空线设成模板长度并加下划线
                t = ''.join(x.text or '' for x in r.findall(qn('w:t')))
                if t.strip() == '' and len(t) >= 10:
                    for x in r.findall(qn('w:t')):
                        x.text = ' ' * REHAB_BLANK
                        x.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
                    rPr = r.find(qn('w:rPr'))
                    if rPr is None:
                        rPr = OxmlElement('w:rPr')
                        r.insert(0, rPr)
                    if rPr.find(qn('w:u')) is None:
                        u = OxmlElement('w:u')
                        u.set(qn('w:val'), 'single')
                        rPr.append(u)
                    break
            grp = [r for r in runs if _is_group_run(r)]
            if not grp:
                done.append('康复措施: 已是图片形式，跳过')
                continue
            png = os.path.join(tmpdir, 't8_group_rehab.png')
            W, H = make_group(REHAB_LEFT_PX, REHAB_W_PX, {0: '1', 1: '4'}, png)
            _put_image(doc, p, grp, png, W * 72.0 / DPI, H * 72.0 / DPI)
            done.append('康复措施: %d run -> 1 张方框组图 (%dx%dpx)' % (len(grp), W, H))
    doc.save(path)
    return done


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('用法: python3 postfix_t8_groupimg.py <docx路径>')
    target = os.path.abspath(sys.argv[1])
    if not target.lower().endswith('.docx') or not os.path.isfile(target):
        sys.exit('错误: 目标必须是存在的 .docx 文件: %s' % target)
    for line in postfix(target):
        print(line)
    print('已写回:', target)
