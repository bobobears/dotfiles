#!/usr/bin/env python3
"""DSA ETF 日线补齐（新浪优先，腾讯兜底）

用法: cd ~/dsa && ./venv/bin/python fetch_etf_daily.py [datalen]
幂等：只 INSERT 库内缺失的日期，可反复跑。
"""
import json, sqlite3, urllib.request, sys
from datetime import datetime

DB = '/home/bobobears/dsa/data/stock_analysis.db'
ETFS = {'159819': 'sz', '515080': 'sh', '510500': 'sh'}
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
N = int(sys.argv[1]) if len(sys.argv) > 1 else 15


def _get(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': UA, 'Referer': 'https://finance.sina.com.cn'})
    return urllib.request.urlopen(req, timeout=20).read().decode('utf-8', errors='replace')


def fetch_sina(code, pref):
    url = ('https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/'
           f'CN_MarketData.getKLineData?symbol={pref}{code}&scale=240&ma=no&datalen={N}')
    data = json.loads(_get(url))
    # date, open, high, low, close, volume(股)
    return [[r['day'], float(r['open']), float(r['high']), float(r['low']),
             float(r['close']), float(r['volume'])] for r in data]


def fetch_tencent(code, pref):
    url = f'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={pref}{code},day,,,{N},'
    node = json.loads(_get(url))['data'][f'{pref}{code}']
    key = 'day' if 'day' in node else 'qfqday'   # 部分 ETF 没有 qfqday
    # date, open, close, high, low, volume(手) -> 转股
    return [[r[0], float(r[1]), float(r[3]), float(r[4]), float(r[2]), float(r[5]) * 100]
            for r in node[key]]


conn = sqlite3.connect(DB)
cur = conn.cursor()
total_added = 0
report = []

for code, pref in ETFS.items():
    rows, src = None, ''
    for fn, name in ((fetch_sina, 'sina'), (fetch_tencent, 'tencent')):
        try:
            rows = fn(code, pref)
            if rows:
                src = name
                break
        except Exception as e:
            src = f'{name}失败:{str(e)[:40]}'
    if not rows:
        report.append(f'  x {code}: {src}')
        continue

    added = 0
    prev_close = None
    for date, o, h, l, c, vol in rows:
        cur.execute('SELECT close FROM stock_daily WHERE code=? AND date=?', (code, date))
        ex = cur.fetchone()
        if ex:
            prev_close = ex[0]
            continue
        if prev_close is None:
            cur.execute('SELECT close FROM stock_daily WHERE code=? AND date<? '
                        'ORDER BY date DESC LIMIT 1', (code, date))
            pc = cur.fetchone()
            prev_close = pc[0] if pc else None
        pct = round((c / prev_close - 1) * 100, 4) if prev_close else None
        cur.execute('''INSERT INTO stock_daily
            (code, date, open, high, low, close, volume, amount, pct_chg,
             data_source, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
            (code, date, o, h, l, c, vol, None, pct, src.capitalize() + 'Fetcher',
             datetime.now().isoformat(), datetime.now().isoformat()))
        added += 1
        prev_close = c
    total_added += added
    report.append(f'  ok {code}: 最新 {rows[-1][0]} ({src})，新增 {added} 条')

conn.commit()
print(f'ETF 补齐完成，共新增 {total_added} 条')
for r in report:
    print(r)
for code in ETFS:
    cur.execute('SELECT MAX(date), COUNT(*) FROM stock_daily WHERE code=?', (code,))
    r = cur.fetchone()
    print(f'  {code}: {r[0]}  共 {r[1]} 条')
conn.close()
