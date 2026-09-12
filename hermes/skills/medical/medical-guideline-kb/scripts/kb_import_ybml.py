#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《国家基本医疗保险、生育保险和工伤保险药品目录（2025年）》PDF 解析入库
用法: python3 kb_import_ybml.py <pdf路径> [--dry]

结构(按页):
  p9-82   西药部分     10列 [ATC码,分类名x4,甲乙类,编号,药品名称,剂型,备注]
  p83-125 中成药部分    9列 [代码,分类名x4,甲乙类,编号,药品名称,备注]
  p126-191 谈判竞价药品 11列 [代码,分类名x4,甲乙类,编号,药品名称,医保支付标准,备注,协议有效期]
  p192-201 中药饮片     6列 [序号,饮片名称,备注,序号,饮片名称,备注] (双栏)

输出:
  - SQLite knowledge.db 新表 yb_drugs（机器可检索主副本）
  - medical/医保监管/2025年国家医保药品目录-*.md（总览+四部分明细）
  - source/国家医保智能监管知识库规则库/../2025年版国家医保药品目录-原文.pdf
"""
import os, re, sys, json, shutil, sqlite3
from datetime import datetime

KB_ROOT = os.path.expanduser('~/private_db/knowledge')
DB_PATH = os.path.join(KB_ROOT, 'db', 'knowledge.db')
CAT = '医保监管'
CAT_DIR = os.path.join(KB_ROOT, 'medical', CAT)
SRC_DIR = os.path.join(KB_ROOT, 'source', '国家医保智能监管知识库规则库')


def clean(v):
    if v is None:
        return ''
    s = str(v).replace('\n', '').replace('\r', '')
    s = re.sub(r'\s+', '', s)  # 目录内文本无必要空格，全去
    return s.strip()


def md_esc(s):
    return (s or '').replace('|', '\\|')


def parse(pdf_path, dry=False):
    import pdfplumber
    drugs = []   # dict: section, atc_code, category_path, class_ab, seq_no, drug_name, dosage_form, pay_standard, remark, valid_period
    tcm = []     # (seq, name, flag)

    with pdfplumber.open(pdf_path) as pdf:
        n_pages = len(pdf.pages)
        for pi in range(n_pages):
            page = pdf.pages[pi]
            tbls = page.extract_tables()
            if not tbls or not tbls[0]:
                continue
            t = tbls[0]
            ncols = len(t[0])
            # 只处理正文表格页: p9-201; 凡例/目录页的小表跳过
            if pi < 8 or pi > 200 or ncols not in (6, 9, 10, 11):
                continue

            # 中药饮片部分: 6列双栏
            if ncols == 6 and pi >= 190:
                for r in t:
                    r = [clean(c) for c in r] + [''] * (6 - len(r))
                    if r[0] == '序号':
                        continue
                    for off in (0, 3):
                        seq_s, name, flag = r[off], r[off+1], r[off+2]
                        if re.fullmatch(r'\d+', seq_s) and name:
                            tcm.append((int(seq_s), name, '□' in flag))
                continue

            # 药品部分(西药/中成药/谈判): 按页码定 section (pi为0基索引)
            if pi < 82:
                section = '西药'                      # p9-82
            elif pi < 125:
                section = '中成药'                    # p83-125
            elif pi < 180:
                section = '协议期内谈判药品(西药)'     # p126-180, 编号1~399
            elif pi < 188:
                section = '协议期内谈判药品(中成药)'   # p181-188, ZA分类, 编号1~61
            else:
                section = '竞价药品'                  # p189-191, XA/XC分类, 编号1~12

            cat_stack = ['', '', '', '']   # 4级分类名
            for r in t:
                raw = [str(c) if c else '' for c in r] + [''] * (ncols - len(r))
                code, ab, seq_s = clean(raw[0]), clean(raw[5]), clean(raw[6])

                # 表头行跳过
                if code == '药品分类代码':
                    continue

                # 分类行: 有ATC码且无编号/名称
                if re.fullmatch(r'[A-Z][A-Z0-9X]{1,6}', code) and not seq_s:
                    c1, c2, c3, c4 = (clean(raw[i]) for i in range(1, 5))
                    cat_stack = [c1 or cat_stack[0], c2 or cat_stack[1],
                                 c3 or cat_stack[2], c4 or cat_stack[3]]
                    continue

                # 数据行: 甲乙类 + 编号(纯数字或★(n))
                m = re.fullmatch(r'(\d+)', seq_s) or re.fullmatch(r'★\((\d+)\)', seq_s)
                if ab not in ('甲', '乙') or not m:
                    continue

                # 名称单元格可能多行: ①长药名被列宽折断(应合并) ②同一编号下多个不同规格药品名竖排堆叠(应拆分)
                name_lines = [clean(x) for x in raw[7].split('\n')]
                name_lines = [x for x in name_lines if x]
                if not name_lines:
                    continue

                # 含≥2个不同罗马数字 → 确定是堆叠的不同药品(如 瑞格列奈二甲双胍Ⅰ/Ⅱ)，拆分;
                # 否则合并回一个名字(长名折行,或无罗马数字的堆叠——合并后仍可用 LIKE 检索到)
                romans = set()
                for ln in name_lines:
                    romans |= set(re.findall(r'[ⅠⅡⅢⅣⅤ]', ln))
                if len(name_lines) > 1 and len(romans) >= 2:
                    final_names = name_lines
                else:
                    final_names = [''.join(name_lines)]

                # 剂型/备注/支付标准/有效期: 单值广播(remark多行是长文本折行，合并回一句)
                if ncols == 10:      # 西药
                    form = clean(raw[8]); remark = re.sub(r'\s+', '', raw[9])
                    pay_std, valid = '', ''
                elif ncols == 9:     # 中成药
                    form = ''; remark = re.sub(r'\s+', '', raw[8])
                    pay_std, valid = '', ''
                else:                # 谈判/竞价 11列
                    form = ''
                    pay_std = re.sub(r'\s+', '', raw[8]); remark = re.sub(r'\s+', '', raw[9])
                    valid = re.sub(r'\s+', '', raw[10])

                for nm in final_names:
                    drugs.append({
                        'section': section,
                        'atc_code': code,
                        'category_path': ' > '.join(x for x in cat_stack if x),
                        'class_ab': ab,
                        'seq_no': int(m.group(1)),
                        'drug_name': nm,
                        'dosage_form': form,
                        'pay_standard': pay_std,
                        'remark': remark,
                        'valid_period': valid,
                    })
    return drugs, tcm


def main():
    pdf_path = sys.argv[1]
    dry = '--dry' in sys.argv

    drugs, tcm = parse(pdf_path)

    # 校验官方数字
    from collections import Counter
    cnt = Counter(d['section'] for d in drugs)
    print("解析结果:")
    print(f"  西药: {cnt.get('西药',0)} (官方1446)")
    print(f"  中成药: {cnt.get('中成药',0)} (官方1335)")
    n_tx = cnt.get('协议期内谈判药品(西药)', 0)
    n_tz = cnt.get('协议期内谈判药品(中成药)', 0)
    n_jj = cnt.get('竞价药品', 0)
    print(f"  谈判药品: {n_tx+n_tz} (官方472, 其中西药{n_tx}/中成药{n_tz})")
    print(f"  竞价药品: {n_jj}")
    print(f"  中药饮片(准予支付): {len(tcm)} (官方892), 其中□单方不付: {sum(1 for x in tcm if x[2])}")

    # 编号连续性检查
    for sec, expect_max in [('西药', 1446), ('中成药', 1335),
                            ('协议期内谈判药品(西药)', 399), ('协议期内谈判药品(中成药)', 61),
                            ('竞价药品', 12)]:
        seqs = sorted(set(d['seq_no'] for d in drugs if d['section'] == sec))
        missing = [i for i in range(1, expect_max+1) if i not in set(seqs)]
        print(f"  {sec}: 最大编号={max(seqs) if seqs else 0}, 缺失编号数={len(missing)}",
              (f"前5个缺失: {missing[:5]}" if missing else ""))

    if dry:
        return

    os.makedirs(CAT_DIR, exist_ok=True)
    os.makedirs(SRC_DIR, exist_ok=True)
    shutil.copy2(pdf_path, os.path.join(SRC_DIR, '2025年版国家医保药品目录-原文.pdf'))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # 幂等清理
    if _table_exists(cur, 'yb_drugs'):
        cur.execute('''DELETE FROM yb_drugs WHERE section IN
            ('西药','中成药','协议期内谈判药品(西药)','协议期内谈判药品(中成药)','竞价药品','中药饮片')''')
    cur.execute("DELETE FROM documents WHERE category=? AND type='药品目录'", (CAT,))
    cur.execute('''CREATE TABLE IF NOT EXISTS yb_drugs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        section TEXT, atc_code TEXT, category_path TEXT, class_ab TEXT,
        seq_no INTEGER, drug_name TEXT, dosage_form TEXT, pay_standard TEXT,
        remark TEXT, valid_period TEXT)''')
    cur.execute('CREATE INDEX IF NOT EXISTS ix_ybd_name ON yb_drugs(drug_name)')
    cur.execute('CREATE INDEX IF NOT EXISTS ix_ybd_section ON yb_drugs(section)')
    cur.execute('''CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, type TEXT, source TEXT,
        url TEXT, published TEXT, journal TEXT, doi TEXT, authors TEXT, tags TEXT,
        keywords TEXT, category TEXT, file_path TEXT, imported_at TEXT)''')

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cur.executemany('''INSERT INTO yb_drugs
        (section,atc_code,category_path,class_ab,seq_no,drug_name,dosage_form,pay_standard,remark,valid_period)
        VALUES (?,?,?,?,?,?,?,?,?,?)''',
        [(d['section'], d['atc_code'], d['category_path'], d['class_ab'], d['seq_no'],
          d['drug_name'], d['dosage_form'], d['pay_standard'], d['remark'], d['valid_period']) for d in drugs])
    cur.executemany('''INSERT INTO yb_drugs
        (section,atc_code,category_path,class_ab,seq_no,drug_name,dosage_form,pay_standard,remark,valid_period)
        VALUES (?,?,?,?,?,?,?,?,?,?)''',
        [('中药饮片', '', '基金准予支付的中药饮片', '', s, n, '', '', '□' if f else '', '') for (s, n, f) in tcm])

    # ---- markdown: 总览 + 四部分 ----
    def section_md(sec_title, rows, cols):
        hdr = '| ' + ' | '.join(cols) + ' |'
        sep = '|' + '|'.join(['---']*len(cols)) + '|'
        lines = [hdr, sep]
        for r in rows:
            lines.append('| ' + ' | '.join(md_esc(str(x)) if x is not None else '' for x in r) + ' |')
        return '\n'.join(lines)

    def front(title, kw):
        return f"""---
title: "{title}"
type: 药品目录
category: {CAT}
source: "国家医疗保障局、人力资源社会保障部（医保发〔2025〕33号）"
url: "https://www.nhsa.gov.cn/art/2025/12/7/art_104_18970.html"
published: 2025-12-07
authors: "国家医疗保障局、人力资源社会保障部"
tags: ["医保监管", "药品目录", "2025年版"]
keywords: "{kw}"
imported_at: {now}
---

# {title}

> **来源**: 医保发〔2025〕33号《关于印发〈国家基本医疗保险、生育保险和工伤保险药品目录〉以及〈商业健康保险创新药品目录〉（2025年）的通知》
> **执行日期**: 2026-01-01 起正式执行，2024年版同时废止
> **原始文件**: `source/国家医保智能监管知识库规则库/2025年版国家医保药品目录-原文.pdf`（202页）
> **机器可检索副本**: SQLite `knowledge.db` 表 `yb_drugs`

"""

    # 总览
    n_x = cnt.get('西药', 0); n_z = cnt.get('中成药', 0)
    n_tx = cnt.get('协议期内谈判药品(西药)', 0)
    n_tz = cnt.get('协议期内谈判药品(中成药)', 0)
    n_jj = cnt.get('竞价药品', 0)
    n_t = n_tx + n_tz
    overview = front("2025年版国家医保药品目录（总览）", "国家医保药品目录,2025年,凡例,甲乙类") + f"""## 目录构成

| 部分 | 品种数 | 说明 |
|------|:--:|------|
| 西药 | {n_x} | 甲类393个，其余乙类；按ATC分类 |
| 中成药 | {n_z} | 含民族药95个；甲类246个，其余乙类 |
| 协议期内谈判药品（西药） | {n_tx} | 按乙类支付，执行全国统一医保支付标准；官方口径"西药411"含竞价{n_jj}个 |
| 协议期内谈判药品（中成药） | {n_tz} | 同上 |
| 竞价药品 | {n_jj} | 同通用名基金支付基准 |
| **合计** | **{n_x+n_z+n_t+n_jj}** | — |
| 中药饮片（准予支付） | {len(tcm)} | 其中标注"□"的单独使用统筹基金不予支付 |

## 凡例要点

1. 目录是医保基金**支付标准**，不是用药限制——临床医师根据病情开具处方、参保人购药不受目录限制
2. 同一品种只编一个号，重复出现（不同剂型）标注"★(编号)"
3. 中药饮片部分标注"**□**"的指单独使用时统筹基金不予支付，且全部由这些饮片组成的处方也不予支付
4. 限生育保险支付的品种4个、限工伤保险支付的品种5个（见各药品备注）
5. 中成药中含"麝香"指人工麝香、"牛黄"指人工/培植/体外培育牛黄；含天然麝香、天然牛黄的不予支付
6. 谈判/竞价药品医保支付标准带"*"标识的，不得在公开途径公布

## 检索方法（SQLite）

```sql
-- 查某药是否在目录内 + 甲乙类 + 备注(限定支付范围)
SELECT section, class_ab, seq_no, drug_name, dosage_form, remark FROM yb_drugs WHERE drug_name LIKE '%阿莫西林%';

-- 查谈判/竞价药品支付标准与有效期
SELECT section, drug_name, pay_standard, valid_period FROM yb_drugs
WHERE (section LIKE '协议期内谈判药品%' OR section='竞价药品') AND drug_name LIKE '%奥希替尼%';

-- 查单方不予支付的中药饮片
SELECT seq_no, drug_name FROM yb_drugs WHERE section='中药饮片' AND remark='□';
```

## 明细文件

- `2025年国家医保药品目录-西药部分.md`（{n_x}条）
- `2025年国家医保药品目录-中成药部分.md`（{n_z}条）
- `2025年国家医保药品目录-谈判竞价药品部分.md`（{n_t+n_jj}条，含支付标准/有效期）
- `2025年国家医保药品目录-中药饮片部分.md`（{len(tcm)}条）

"""
    files = [('2025年国家医保药品目录-总览.md', overview, '2025年版国家医保药品目录（总览）')]

    # 西药
    rows = [(d['atc_code'], d['category_path'].split(' > ')[-1] if d['category_path'] else '',
             d['class_ab'], d['seq_no'], d['drug_name'], d['dosage_form'], d['remark'])
            for d in drugs if d['section'] == '西药']
    files.append(('2025年国家医保药品目录-西药部分.md',
                  front("2025年版国家医保药品目录·西药部分", "西药,ATC,甲乙类") + section_md('西药', rows,
                  ['分类代码','末级分类','甲乙类','编号','药品名称','剂型','备注']), '2025年版国家医保药品目录（西药部分）'))

    # 中成药
    rows = [(d['atc_code'], d['category_path'].split(' > ')[-1] if d['category_path'] else '',
             d['class_ab'], d['seq_no'], d['drug_name'], d['remark'])
            for d in drugs if d['section'] == '中成药']
    files.append(('2025年国家医保药品目录-中成药部分.md',
                  front("2025年版国家医保药品目录·中成药部分", "中成药,甲乙类") + section_md('中成药', rows,
                  ['分类代码','末级分类','甲乙类','编号','药品名称','备注']), '2025年版国家医保药品目录（中成药部分）'))

    # 谈判竞价(西药+中成药+竞价)
    rows = [(d['section'], d['atc_code'], d['class_ab'], d['seq_no'], d['drug_name'],
             d['pay_standard'], d['remark'], d['valid_period'])
            for d in drugs if d['section'] in ('协议期内谈判药品(西药)', '协议期内谈判药品(中成药)', '竞价药品')]
    files.append(('2025年国家医保药品目录-谈判竞价药品部分.md',
                  front("2025年版国家医保药品目录·协议期内谈判药品（含竞价）", "谈判药品,支付标准,竞价") + section_md('谈判药品', rows,
                  ['子节','分类代码','甲乙类','编号','药品名称','医保支付标准','备注(限定支付范围)','协议有效期']), '2025年版国家医保药品目录（谈判竞价药品部分）'))

    # 中药饮片
    rows = [(s, n, '□' if f else '') for (s, n, f) in tcm]
    files.append(('2025年国家医保药品目录-中药饮片部分.md',
                  front("2025年版国家医保药品目录·中药饮片部分", "中药饮片,单方不予支付") + section_md('中药饮片', rows,
                  ['序号','饮片名称','备注(□=单方使用统筹基金不予支付)']), '2025年版国家医保药品目录（中药饮片部分）'))

    for fname, content, title in files:
        path = os.path.join(CAT_DIR, fname)
        with open(path, 'w') as fh:
            fh.write(content)
        cur.execute('''INSERT INTO documents
            (title,type,source,url,published,journal,doi,authors,tags,keywords,category,file_path,imported_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (title, '药品目录', '国家医疗保障局、人力资源社会保障部（医保发〔2025〕33号）',
             'https://www.nhsa.gov.cn/art/2025/12/7/art_104_18970.html', '2025-12-07', '', '',
             '国家医疗保障局、人力资源社会保障部', '医保监管,药品目录,2025年版',
             f'国家医保药品目录,2025年,{title}', CAT, path, now))

    conn.commit()
    print(f"\n入库完成: yb_drugs 共 {cur.execute('SELECT COUNT(*) FROM yb_drugs').fetchone()[0]} 条")
    print(f"documents 总数: {cur.execute('SELECT COUNT(*) FROM documents').fetchone()[0]}")
    conn.close()


def _table_exists(cur, name):
    return cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


if __name__ == '__main__':
    main()
