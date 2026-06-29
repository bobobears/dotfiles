#!/usr/bin/env python3
"""A股选股器 - 完整版 (含趋势判断)

使用方法:
  python3 screener_full.py
  
会自动连接数据源获取沪深全部A股的实时行情、ROE和趋势数据，
并根据设定的条件筛选出符合标准的股票。

条件设置: 编辑下方 conditions 字典
数据依赖: pip install akshare tushare pandas
"""

import urllib.request, json, time, re
import pandas as pd
import akshare as ak
import warnings
warnings.filterwarnings('ignore')

pd.set_option('display.max_columns', 20)
pd.set_option('display.width', 200)

# ============================
# 配置
# ============================
CONDITIONS = {
    'circ_mv_min': 50,       # 流通市值下限(亿)
    'circ_mv_max': 100,      # 流通市值上限(亿)
    'vol_ratio_min': 1.5,    # 量比下限
    'roe_min': 10.0,         # ROE下限(%)
    'pct_today_min': 0,      # 今日涨幅下限
    'exclude_st': True,      # 排除ST股
}

print("=" * 80)
print("📊 A股选股筛选器")
c = CONDITIONS
print(f"条件: ①流通市值{c['circ_mv_min']}-{c['circ_mv_max']}亿 "
      f"②量比>{c['vol_ratio_min']} ③今日涨幅>{c['pct_today_min']}% ④ROE≥{c['roe_min']}%"
      + (" ⑤排除ST" if c['exclude_st'] else ""))
print("=" * 80)

# ============================
# Step 1: 代码列表
# ============================
print("\n📥 [1/5] 获取全A股代码列表...")
headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.sina.com.cn/'}
all_stocks = []
for node in ['sh_a', 'sz_a']:
    page = 1
    while True:
        url = f"https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeDataSimple?page={page}&num=10000&sort=symbol&asc=1&node={node}&symbol=&_s_r_a=page"
        try:
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=15)
            data = resp.read().decode('gbk').strip()
            if not data or data == 'null': break
            codes = json.loads(re.sub(r'/\*.*?\*/', '', data, flags=re.DOTALL))
            if not codes: break
            for s in codes:
                c = s.get('code', '')
                n = s.get('name', '')
                if c and not c.startswith('8') and (not c['exclude_st'] or 'ST' not in n):
                    all_stocks.append((c, n))
            if len(codes) < 10000: break
            page += 1
        except: break
print(f"✅ {len(all_stocks)} 只沪深A股")

stock_codes = [s[0] for s in all_stocks]
stock_names = {s[0]: s[1] for s in all_stocks}

# ============================
# Step 2: 腾讯行情 - 批量获取
# ============================
print(f"\n📥 [2/5] 腾讯API批量行情...")
market_data = []
for i in range(0, len(stock_codes), 100):
    batch = stock_codes[i:i+100]
    qs = ','.join([f"sh{c}" if c.startswith('6') else f"sz{c}" for c in batch])
    try:
        req = urllib.request.Request(f"https://qt.gtimg.cn/q={qs}", headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.qq.com/'})
        text = urllib.request.urlopen(req, timeout=30).read().decode('gbk')
        for line in text.strip().split(';'):
            if '=' not in line: continue
            parts = line.split('="')[1].rstrip('";').split('~')
            if len(parts) < 50: continue
            market_data.append({
                'code': parts[2],
                'name': parts[1],
                'price': float(parts[3]) if parts[3] else 0,
                'pct': float(parts[38]) if len(parts)>38 and parts[38] else 0,
                'circ_mv': float(parts[44]) if len(parts)>44 and parts[44] else 0,
                'vol_ratio': float(parts[46]) if len(parts)>46 and parts[46] else 0,
            })
    except: pass
    time.sleep(0.2)
    if (i//100+1) % 10 == 0:
        print(f"   进度: {min(i+100, len(stock_codes))}/{len(stock_codes)}")
print(f"✅ {len(market_data)} 条行情数据")

# ============================
# Step 3: 初步筛选
# ============================
print(f"\n🔍 [3/5] 初步筛选...")
df = pd.DataFrame(market_data)
mv_cond = (df['circ_mv'] >= c['circ_mv_min']) & (df['circ_mv'] <= c['circ_mv_max'])
vol_cond = df['vol_ratio'] > c['vol_ratio_min']
up_cond = df['pct'] > c['pct_today_min']
candidates = df[mv_cond & vol_cond & up_cond].sort_values('vol_ratio', ascending=False)
print(f"流通市值{c['circ_mv_min']}-{c['circ_mv_max']}亿: {mv_cond.sum()} 只")
print(f"+量比>{c['vol_ratio_min']}: {(mv_cond & vol_cond).sum()} 只")
print(f"+涨幅>{c['pct_today_min']}%: {len(candidates)} 只")

# ============================
# Step 4: ROE获取(同花顺)
# ============================
print(f"\n📥 [4/5] 获取ROE数据（同花顺）...")
candidate_codes = candidates.head(50)['code'].tolist()
roe_data = {}
for idx, code in enumerate(candidate_codes):
    try:
        df_fin = ak.stock_financial_abstract_ths(symbol=code)
        if '净资产收益率' in df_fin.columns:
            roe_val = df_fin['净资产收益率'].iloc[0]
            if isinstance(roe_val, str):
                roe_val = float(roe_val.replace('%', ''))
            roe_data[code] = roe_val
    except: pass
    time.sleep(0.3)
    if (idx+1) % 10 == 0:
        print(f"   进度: {idx+1}/{len(candidate_codes)} ({len(roe_data)}只成功)")
print(f"✅ 获取到 {len(roe_data)} 只ROE数据")

# ============================
# Step 5: 趋势分析(搜狐K线)
# ============================
print(f"\n📥 [5/5] 趋势分析（搜狐日K均线）...")
roe_candidates = [c for c in candidate_codes if c in roe_data and roe_data[c] >= c['roe_min']]
print(f"ROE≥{c['roe_min']}%的股票: {len(roe_candidates)} 只")

def get_kline_sohu(code):
    prefix = "cn_" + ("sh" if code.startswith('6') else "sz")
    url = f"https://q.stock.sohu.com/hisHq?code={prefix}{code}&start=20260401&end=20260626"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        if data[0].get('status') == 0 and data[0].get('hq'):
            records = []
            for row in data[0]['hq']:
                records.append({'close': float(row[1]), 'volume': float(row[7]) or 0})
            return records
    except: pass
    return []

def check_trend(records):
    if len(records) < 20: return False, 0, "数据不足"
    closes = [r['close'] for r in records]
    ma5 = sum(closes[-5:])/5
    ma10 = sum(closes[-10:])/10
    ma20 = sum(closes[-20:])/20
    cur = closes[-1]
    score = 0
    reasons = []
    if cur > ma5: score += 25; reasons.append(f"价>MA5({ma5:.2f})")
    if cur > ma20: score += 25; reasons.append(f"价>MA20({ma20:.2f})")
    if ma5 > ma10 > ma20: score += 30; reasons.append("多头排列")
    if len(closes) >= 5:
        chg5 = (cur/closes[-5]-1)*100
        if chg5 > 0: score += 10; reasons.append(f"5日涨{chg5:.1f}%")
    return score >= 50, score, ' | '.join(reasons)

# 如果搜狐K线不可用，回退到Tushare
def check_trend_tushare(code):
    """备用: 使用Tushare日K线判断趋势"""
    import tushare as ts
    pro = ts.pro_api()  # 需要在环境变量或脚本中设置token
    try:
        ts_code = code + (".SH" if code.startswith('6') else ".SZ")
        df = pro.daily(ts_code=ts_code, start_date='20260501', end_date='20260626')
        if df is not None and len(df) >= 20:
            df = df.sort_values('trade_date')
            closes = df['close'].values
            ma5 = closes[-5:].mean()
            ma10 = closes[-10:].mean()
            ma20 = closes[-20:].mean()
            cur = closes[-1]
            score = 0
            if cur > ma5: score += 25
            if cur > ma20: score += 25
            if ma5 > ma10 > ma20: score += 30
            if cur > closes[-5]: score += 10
            return score >= 50, score, f"MA5={ma5:.2f} MA10={ma10:.2f} MA20={ma20:.2f}"
    except: pass
    return False, 0, "数据不可用"

trend_results = []
for idx, code in enumerate(roe_candidates):
    klines = get_kline_sohu(code)
    if len(klines) >= 20:
        is_up, score, reason = check_trend(klines)
    else:
        is_up, score, reason = check_trend_tushare(code)
    
    r = candidates[candidates['code']==code].iloc[0]
    trend_results.append({
        'code': code,
        'name': stock_names.get(code, ''),
        'price': r['price'],
        'pct': r['pct'],
        'circ_mv': r['circ_mv'],
        'vol_ratio': r['vol_ratio'],
        'roe': roe_data.get(code, 0),
        'trend': '📈上升趋势' if is_up else '📉震荡/下跌',
        'score': score,
        'detail': reason,
    })
    time.sleep(0.2)
    if (idx+1) % 5 == 0:
        print(f"   趋势: {idx+1}/{len(roe_candidates)}")

# ============================
# 结果输出
# ============================
print(f"\n{'='*80}")
print(f"🏆 最终推荐结果")
print(f"{'='*80}")

if trend_results:
    trend_results.sort(key=lambda x: x['score'], reverse=True)
    up_results = [r for r in trend_results if '上升' in r['trend']]
    print(f"\n{'代码':<8} {'名称':<8} {'现价':<7} {'涨幅%':<7} {'流通市值':<9} {'量比':<6} {'ROE%':<6} {'趋势':<12} {'详情'}")
    print(f"{'-'*80}")
    for r in up_results:
        print(f"{r['code']:<8} {r['name']:<8} {r['price']:<7.2f} {r['pct']:<+7.2f} {r['circ_mv']:<9.1f} {r['vol_ratio']:<6.2f} {r['roe']:<6.2f} {r['trend']:<12} {r['detail'][:30]}")
    
    print(f"\n📌 汇总: {len(up_results)}/{len(trend_results)} 只满足全部条件")
    print(f"   条件: 流通市值{c['circ_mv_min']}-{c['circ_mv_max']}亿 + 量比>{c['vol_ratio_min']} + 今日上涨 + ROE≥{c['roe_min']}% + 均线上升趋势")
else:
    print("❌ 无完全符合条件的股票")
