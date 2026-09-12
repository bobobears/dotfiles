#!/usr/bin/env python3
"""
知识库入库脚本（可复用）
用法: python3 kb_import.py <正文txt路径> <元数据JSON路径> <类别> <文件名>

元数据JSON字段: title, source, url, published, journal, doi, authors, tags, keywords, type
"""
import os
import sys
import json
import sqlite3
import shutil
from datetime import datetime

KB_ROOT = os.path.expanduser('~/private_db/knowledge')
DB_PATH = os.path.join(KB_ROOT, 'db', 'knowledge.db')


def main():
    if len(sys.argv) < 5:
        print('用法: python3 kb_import.py <正文txt> <元数据JSON> <类别> <文件名>')
        sys.exit(1)

    txt_path = sys.argv[1]
    meta_path = sys.argv[2]
    category = sys.argv[3]  # e.g. 指南规范
    filename = sys.argv[4]  # e.g. 2026-xxx.md

    with open(meta_path) as f:
        meta = json.load(f)
    with open(txt_path) as f:
        body = f.read().strip()

    # 去掉开头引导行
    lines = body.split('\n')
    while lines and ('点击标题下' in lines[0] or '点击文末' in lines[0]):
        lines.pop(0)
    body = '\n'.join(lines).strip()

    cat_dir = os.path.join(KB_ROOT, 'medical', category)
    src_dir = os.path.join(KB_ROOT, 'source')
    os.makedirs(cat_dir, exist_ok=True)
    os.makedirs(src_dir, exist_ok=True)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    md = f"""---
title: "{meta['title']}"
type: {meta.get('type', category)}
source: "{meta.get('source', '')}"
url: "{meta.get('url', '')}"
published: {meta.get('published', '')}
journal: "{meta.get('journal', '')}"
doi: {meta.get('doi', '')}
authors: "{meta.get('authors', '')}"
tags: [{', '.join('"' + t.strip() + '"' for t in meta.get('tags', '').split(','))}]
keywords: "{meta.get('keywords', '')}"
imported_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
---

# {meta['title']}

> **来源**: {meta.get('source', '')}
> **刊于**: {meta.get('journal', '')}
> **DOI**: {meta.get('doi', '')}
> **发布日期**: {meta.get('published', '')}
> **作者**: {meta.get('authors', '')}

---

{body}
"""

    md_file = os.path.join(cat_dir, filename)
    with open(md_file, 'w') as f:
        f.write(md)

    # 原文备份（如果源HTML存在且与txt同目录）
    html_candidate = txt_path.replace('.txt', '.html')
    if os.path.exists(html_candidate):
        shutil.copy(html_candidate, os.path.join(src_dir, f'{filename.replace(".md", "")}-原文.html'))

    # SQLite 索引
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        type TEXT,
        source TEXT,
        url TEXT,
        published TEXT,
        journal TEXT,
        doi TEXT,
        authors TEXT,
        tags TEXT,
        keywords TEXT,
        category TEXT,
        file_path TEXT,
        imported_at TEXT
    )''')
    cur.execute('''INSERT INTO documents
        (title, type, source, url, published, journal, doi, authors, tags, keywords, category, file_path, imported_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (meta['title'], meta.get('type', category), meta.get('source', ''), meta.get('url', ''),
         meta.get('published', ''), meta.get('journal', ''), meta.get('doi', ''), meta.get('authors', ''),
         meta.get('tags', ''), meta.get('keywords', ''), category, md_file,
         datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()

    cur.execute('SELECT COUNT(*) FROM documents')
    total = cur.fetchone()[0]
    print(f'✅ 入库成功！知识库现有 {total} 条记录')
    print(f'   {category}: {meta["title"]}')
    print(f'   文件: {md_file}')
    conn.close()


if __name__ == '__main__':
    main()
