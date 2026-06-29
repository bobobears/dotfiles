# A-Stock Screening Pipeline

Full multi-source pipeline for screening A-share stocks by custom criteria (circulating market cap, volume ratio, uptrend, ROE). Tested on Hermes running in China (Shenzhen).

## Architecture

```
Sina (5000+ codes, 2 calls) 
    → Tencent (batch quotes, 55 calls of 100, ~16s)
    → akshare/THS (ROE, ~0.3s per stock)
    → Tushare (K-line trend, rate-limited 1/min)
```

## Step-by-step Code

### 1. Get Stock Codes (Sina)

```python
import urllib.request, json, re

def get_stock_list():
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.sina.com.cn/'}
    all_stocks = []
    for node in ['sh_a', 'sz_a']:
        page = 1
        while True:
            url = (f"https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php"
                   f"/Market_Center.getHQNodeDataSimple?page={page}&num=10000"
                   f"&sort=symbol&asc=1&node={node}&symbol=&_s_r_a=page")
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
                    if c and not c.startswith('8') and 'ST' not in n:
                        all_stocks.append((c, n))
                if len(codes) < 10000: break
                page += 1
            except: break
    return all_stocks

stocks = get_stock_list()  # Returns [(code, name), ...]
```

### 2. Batch Market Data (Tencent)

```python
def get_tencent_batch(codes, batch_size=100):
    """codes: list of 6-digit stock codes. Returns list of dicts."""
    results = []
    for i in range(0, len(codes), batch_size):
        batch = codes[i:i+batch_size]
        qs = ','.join([f"sh{c}" if c.startswith('6') else f"sz{c}" for c in batch])
        url = f"https://gtimg.cn/q={qs}"  # qt.gtimg.cn
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.qq.com/'})
            text = urllib.request.urlopen(req, timeout=30).read().decode('gbk')
            for line in text.strip().split(';'):
                if '=' not in line: continue
                parts = line.split('="')[1].rstrip('";').split('~')
                if len(parts) < 50: continue
                results.append({
                    'code': parts[2],
                    'name': parts[1],
                    'price': float(parts[3]) if parts[3] else 0,
                    'pct': float(parts[32]) if len(parts)>32 and parts[32] else 0,
                    'circ_mv': float(parts[44]) if len(parts)>44 and parts[44] else 0,
                    'vol_ratio': float(parts[46]) if len(parts)>46 and parts[46] else 0,
                })
        except Exception as e:
            pass
        time.sleep(0.2)
    return results
```

**Field index reference for Tencent 88-field format:**

| Index | Field | Description |
|:-----:|-------|-------------|
| 1 | 股票名称 | Stock name |
| 2 | 股票代码 | 6-digit code |
| 3 | 现价 | Current price |
| 4 | 昨收 | Previous close |
| 6 | 成交量(手) | Volume in lots |
| 32 | 涨跌幅% | Today's change % |
| 44 | 流通市值(亿) | Circulating market cap |
| 45 | 总市值(亿) | Total market cap |
| 46 | 量比 | Volume ratio |

### 3. ROE from 同花顺 (akshare)

```python
import akshare as ak

def get_roe(code):
    """Returns latest ROE % for a stock code."""
    try:
        df = ak.stock_financial_abstract_ths(symbol=code)
        if '净资产收益率' in df.columns:
            val = df['净资产收益率'].iloc[0]
            if isinstance(val, str):
                val = float(val.replace('%', ''))
            return val
    except Exception:
        pass
    return None
```

### 4. Trend Analysis (Tushare K-line)

```python
import tushare as ts
pro = ts.pro_api("your_token")

def get_kline_and_trend(code):
    ts_code = f"{code}.SH" if code.startswith('6') else f"{code}.SZ"
    try:
        df = pro.daily(ts_code=ts_code, start_date="20260501", end_date="20260626")
        if df is None or len(df) < 20: return None
        df = df.sort_values('trade_date').reset_index(drop=True)
        closes = df['close'].values
        
        cur = closes[-1]
        ma5  = sum(closes[-5:]) / 5
        ma10 = sum(closes[-10:]) / 10
        ma20 = sum(closes[-20:]) / 20
        
        score = 0
        if cur > ma5:   score += 20
        if cur > ma20:  score += 20
        if ma5 > ma10 > ma20: score += 25
        elif ma10 > ma20: score += 10
        if closes[-1] > closes[-5]:  score += 15
        if closes[-1] > closes[-10]: score += 10
        
        trend = "强势上升" if score >= 80 else \
                "上升" if score >= 55 else \
                "震荡" if score >= 30 else "下跌趋势"
        
        return {
            'score': score,
            'trend': trend,
            'cur': cur,
            'ma5': ma5, 'ma10': ma10, 'ma20': ma20,
            'pct_5d': (cur/closes[-5]-1)*100,
            'pct_20d': (cur/closes[-20]-1)*100,
        }
    except Exception:
        return None
```

**Free tier rate limit**: 1 call/min. For 20-30 stocks, this takes 20-30 minutes. Use wisely.

## Putting It All Together — Four-Criteria Screen

```python
# Step 1: Get codes
stocks = get_stock_list()  # ~5000 codes

# Step 2: Get market data
market_data = get_tencent_batch([c for c,_ in stocks])

# Step 3: Filter by criteria 1-3
import pandas as pd
df = pd.DataFrame(market_data)
cond = (
    (df['circ_mv'] >= 50) & (df['circ_mv'] <= 100) &
    (df['vol_ratio'] > 1.5) &
    (df['pct'] > 0)  # Today up as preliminary uptrend signal
)
candidates = df[cond].sort_values('vol_ratio', ascending=False)

# Step 4: Get ROE for top 50 candidates
top_codes = candidates.head(50)['code'].tolist()
for code in top_codes:
    roe_data[code] = get_roe(code)
    time.sleep(0.3)

# Step 5: Filter by ROE >= 10%
roe_candidates = [c for c in top_codes if roe_data.get(c, 0) >= 10]

# Step 6: Trend analysis (Tushare, 1 call/min)
for code in roe_candidates:
    trend = get_kline_and_trend(code)  # Waits 1.1s between calls
    if trend and trend['score'] >= 55:
        final.append({code, name, trend, ...})
    time.sleep(1.1)  # Rate limit
```

## Known Issues

- **ST stocks**: Filter by name containing `ST` at the Sina code-list stage
- **北交所**: Codes starting with `8` should be excluded
- **量比异常高**: values >1000 can occur on low-volume stocks (one large order), filter these as anomalies
- **Rate limits**: Tushare free tier severely limits K-line fetching (~1/min); for larger sets use a batch data source or paid tier
- **Tencent field 32 vs 38**: Both contain change % data; field 32 is the most reliable for today's change
- **Name encoding**: Sina returns GBK-encoded names; Tencent returns GBK too; decode properly
