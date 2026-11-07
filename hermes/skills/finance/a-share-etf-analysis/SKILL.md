---
name: a-share-etf-analysis
description: >-
  Query and analyze A-share (Chinese market) ETFs — real-time quotes,
  fund metadata (size, returns, NAV), top holdings, constituent stock
  prices, and cross-referencing. Uses free Chinese web APIs (Sina,
  Eastmoney) that work within mainland China without auth.
---

# A-share ETF Analysis

Query and analyze A-share ETFs (including index ETFs, sector ETFs, and
科创板/创业板 ETFs) using free Chinese web APIs. Covers ETF-level
quotes and full holdings-level constituent stock analysis.

## ETF Code Prefixes

| Code Range | Exchange | Sina Prefix |
|:----------:|:--------:|:-----------:|
| 51xxxx (沪市ETF) | Shanghai | `sh` |
| 58xxxx (科创板ETF) | Shanghai STAR | `sh` |
| 15xxxx (深市ETF) | Shenzhen | `sz` |
| 159xxx (深市ETF) | Shenzhen | `sz` |

**Rule**: codes starting with `5` or `58` → `sh` prefix; codes starting
with `1` or `159` → `sz` prefix.

## Phase 1: Real-time Quote (Sina API)

```python
import urllib.request, re

code = '588200'  # e.g. 科创芯片ETF嘉实
prefix = 'sh' if code.startswith('5') else 'sz'
url = f'https://hq.sinajs.cn/list={prefix}{code}'
req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn"})
data = urllib.request.urlopen(req, timeout=10).read().decode('gb18030')

m = re.search(r'hq_str_\w+="(.*?)"', data)
fields = m.group(1).split(',')
# fields[0]=ETF名称, [1]=开盘价, [2]=昨收, [3]=现价
# [4]=最高, [5]=最低, [8]=成交量(手), [9]=成交额(元)
```

### Key Field Mapping (Sina ETF)

| Index | Field | Unit |
|:-----:|-------|:----:|
| 0 | ETF名称 | string |
| 1 | 开盘价 | float |
| 2 | 昨收 | float |
| 3 | 现价 | float |
| 4 | 最高 | float |
| 5 | 最低 | float |
| 8 | 成交量 | 手 (手=100份) |
| 9 | 成交额 | 元 (divide by 1e8 for 亿) |

## Phase 2: Fund Metadata & Returns (Eastmoney pingzhongdata)

```python
url = f'https://fund.eastmoney.com/pingzhongdata/{code}.js'
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
data = urllib.request.urlopen(req, timeout=10).read()
text = data.decode('utf-8', errors='replace')

# Fund name
import re
fn = re.search(r'fS_name\s*=\s*"([^"]+)"', text)
name = fn.group(1) if fn else code

# Returns (percentage strings)
syls = re.findall(r'syl_(\w+)\s*=\s*"([^"]+)"', text)
# Keys: 1n=近1年, 6y=近6月, 3y=近3月, 1y=近1月

# Stock holdings codes
stock_codes = re.search(r'stockCodesNew\s*=\s*\[(.*?)\]', text)
# Values like "1.688981" — strip the "1." prefix for actual code
```

### Return Rate Labels

| JS Key | Meaning |
|:------:|---------|
| `syl_1n` | 近1年 |
| `syl_6y` | 近6月 |
| `syl_3y` | 近3月 |
| `syl_1y` | 近1月 |

## Phase 3: Top Holdings Detail (Eastmoney f10 Holdings Page)

```python
url = f"http://fundf10.eastmoney.com/FundArchivesDatas.aspx" \
      f"?type=jjcc&code={code}&topline=10&year=&month=&rt=0.1"
req = urllib.request.Request(url, headers={
    "User-Agent": "Mozilla/5.0",
    "Referer": "http://fundf10.eastmoney.com/"
})
data = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')

# Extract HTML from JS wrapper
m = re.search(r'content:\s*"(.*)', data, re.DOTALL)
content_part = m.group(1)
content_part = re.sub(r'"\s*\}\s*$', '', content_part)
content_part = content_part.replace('\\"', '"').replace("\\'", "'")
import html
content = html.unescape(content_part)

# Parse table rows
tables = re.findall(r'<table[^>]*>(.*?)</table>', content, re.DOTALL)
rows = re.findall(r'<tr[^>]*>(.*?)</tr>', tables[0], re.DOTALL)
for row in rows[1:]:  # skip header
    cols = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
    clean = [re.sub(r'<[^>]+>', '', c).strip() for c in cols]
    # clean = [序号, 股票代码, 股票名称, 占净值比, ...]
```

The holdings page returns data as of the **latest quarterly filing** (usually 1-quarter lag). The `stockCodesNew` from pingzhongdata.js gives more current holdings.

## Phase 4: Constituent Stock Real-time Quotes

Batch-query the top-10 holding stock prices using Sina:

```python
stocks = ['688981','688041','688256','688008','688012']  # codes from Phase 2/3
sina_codes = ','.join(['sh' + s for s in stocks])  # All are sh for STAR/SSE
# For SZ stocks: 'sz' + code
# For SH stocks: 'sh' + code

url = f'https://hq.sinajs.cn/list={sina_codes}'
req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn"})
data = urllib.request.urlopen(req, timeout=10).read().decode('gb18030')

for line in data.strip().split('\n'):
    m = re.search(r'hq_str_(\w+)="(.*?)"', line)
    if m:
        fields = m.group(2).split(',')
        stock_id = m.group(1)[2:]  # strip exchange prefix
        name = fields[0]
        cur = float(fields[3])
        yest = float(fields[2])
        pct = (cur - yest) / yest * 100
```

### Sina Stock Quote Field Mapping

| Index | Field | Notes |
|:-----:|-------|-------|
| 0 | 股票名称 | |
| 1 | 开盘价 | |
| 2 | 昨收 | |
| 3 | 现价 | |
| 4 | 最高 | |
| 5 | 最低 | |
| 8 | 成交量 | 手 |
| 9 | 成交额 | 元 |

## Phase 5: ETF Daily K-line (Eastmoney push2his) — 入场择时 / 支撑阻力位

Real-time quote (Phase 1) only gives today's price. For **entry-timing** questions
("今天进 X 合适吗 / 支撑在哪 / 高点回撤多少"), you need the recent daily K-line.
Use Eastmoney push2his — same endpoint as individual stocks, but ETFs need the
`mkt` prefix in `secid`:

```python
import urllib.request, json

code = '512710'
mkt = '1' if code.startswith(('5', '58')) else '0'  # 沪市=1, 深市=0
url = (f'https://push2his.eastmoney.com/api/qt/stock/kline/get'
       f'?secid={mkt}.{code}'
       f'&fields1=f1,f2,f3,f4,f5,f6'
       f'&fields2=f51,f52,f53,f54,f55,f56,f57,f59'   # date,open,close,high,low,vol,amount,pct
       f'&klt=101&fqt=1&end=20500101&lmt=60')
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
data = json.loads(urllib.request.urlopen(req, timeout=10).read().decode('utf-8'))
klines = data['data']['klines']  # each: "YYYY-MM-DD,open,close,high,low,vol,amount,pct"
```

**字段顺序**（fields2 对应）：`date, open, close, high, low, volume, amount, pct_chg`。
⚠️ **close 在 high/low 之前**（同腾讯 ifzq 的坑），别按 OHLC 解析。

- `lmt` = 条数。60 ≈ 3 个月，够算 MA20 + 近月高低点；要一年分位用 `lmt=320`。
- `fqt=1` = 前复权（ETF 一般无分红复权差异，用 `fqt=1` 或 `fqt=0` 都接近，统一 `fqt=1`）。
- `klt=101` = 日线。
- 从 `klines` 取：近月最高/最低、高点回撤%、MA20、支撑区（近期多次探底的价格带）。

**push2his 对 ETF 的 secid 前缀**：沪市 `1.`、深市 `0.`（与个股 secid 规则一致，51xxxx→1，159xxx/15xxxx→0）。

**push2his 失败（HTTP:000 / 静默失败）时**：别在 DNS 上空转，换新浪 K-line（`CN_MarketData.getKLineData`，不复权）或腾讯 ifzq（`qfqday`，close 在 high/low 前）。

## Phase 6: Real-time NAV Estimate (Eastmoney fundgz)

```python
url = f"https://fundgz.1234567.com.cn/js/{code}.js"
req = urllib.request.Request(url, headers={
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://fund.eastmoney.com"
})
data = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
# Returns: jsonpgz({"fundcode":"588200","name":"科创芯片ETF嘉实",
#   "jzrq":"2026-06-26","dwjz":"4.4836","gsz":"4.7028",
#   "gszzl":"4.89","gztime":"2026-06-29 15:00"});
# gsz=盘中估值, gszzl=估值涨跌幅%
```

## 板块内 ETF 横向比较 → 推荐（"XX 板块推荐一只 ETF"）

用户问「军工/红利/科技…板块推荐一只 ETF」时，是**同一板块多只 ETF 横向比较**，不是单只分析。流程：

1. **列出该板块全部有流动性的 ETF**（一般 6-8 只），用 Phase 1 批量取实时价（含成交额/成交量 → 流动性）。
2. **每只取近 3 月 / 6 月 / 1 年收益**（Phase 2 `pingzhongdata` 的 `syl_3y/6y/1n`）。比较时用**回撤弹性**（谁跌得少）而非绝对涨跌——同板块 ETF 涨跌同源，差异在**持仓结构**。
3. **看持仓结构定性**：龙头集中型（前几大都是主机厂/核心厂）vs 宽基分散型。龙头集中型在板块启动时弹性大、但波动也大；分散型稳但弹性小。结合用户「长线 ETF 持有」风格，**龙头集中型通常更优**（少而精）。
4. **输出**：一张表（ETF | 近3月 | 近1年 | 成交额 | 持仓结构 | 定性）→ 推荐 1 只 + 理由（弹性/流动性/结构）→ 次选 1 只。

**坑**：同板块 ETF 名称易混（军工有 512660 军工ETF / 512710 军工龙头 / 512680 军工龙头ETF…），**先核对每只跟踪的指数**再比，别拿两个跟踪不同指数的 ETF 当「同板块」横比。

## Complete Analysis Example

```python
def analyze_etf(code: str):
    """Returns dict with all ETF data."""
    prefix = 'sh' if code.startswith('5') else 'sz'
    
    # 1. Quote
    url1 = f'https://hq.sinajs.cn/list={prefix}{code}'
    # ... parse quote ...
    
    # 2. Metadata
    url2 = f'https://fund.eastmoney.com/pingzhongdata/{code}.js'
    # ... parse name, returns, holdings ...
    
    # 3. Holdings (quarterly)
    url3 = f"http://fundf10.eastmoney.com/FundArchivesDatas.aspx" \
           f"?type=jjcc&code={code}&topline=10"
    # ... parse top 10 ...
    
    # 4. Constituent prices
    # ... batch query from stage 2 codes ...
    
    # 5. NAV estimate
    url5 = f"https://fundgz.1234567.com.cn/js/{code}.js"
    # ... parse gsz ...
    
    return {quote, metadata, holdings, constituent_prices, nav_estimate}
```

## Common Workflows

### List All ETFs in a Sector

Use Eastmoney ETF ranking to find sector ETFs, then analyze each:
```python
# Not needed — you already know the ETF codes for common sectors.
# For discovery, search Eastmoney fund code list by name keywords
# (半导体, 芯片, 新能源, etc.)
```

### Compare ETF vs Constituents Performance

Use the NAV estimate (+pct) from Phase 5 and compare against individual
stock changes from Phase 4 to check if the ETF is tracking correctly or
showing premium/discount relative to portfolio.

## Pitfalls

- **Sina encoding**: Always use `gb18030` (not `utf-8`) for Sina API responses.
- **Holding data lag**: The f10 holdings page is quarterly (up to 3 months stale). `stockCodesNew` from pingzhongdata may be more current but doesn't include weights.
- **ETF vs NAV price**: The market price (Sina Phase 1) and the NAV estimate (fundgz Phase 5) can diverge — the gap is the premium/discount. On high-volatility days, the NAV estimate may lag market price.
- **Stock exchange prefix**: Not all top-10 holdings are on the same exchange. STAR stocks (688xxx) use `sh` prefix. SZ stocks (300xxx, 00xxx) use `sz`.
- **Rate limit**: Sina and fundgz have no auth but will throttle excessive requests. 1-2 queries per second is safe.
- **Code format**: Always pass the **6-digit** code (without exchange letter prefix) to Eastmoney APIs. Sina API needs the exchange prefix (`sh`/`sz`).
- **Holding percentages**: The f10 page shows `占净值比` as a percentage string with `%` suffix. Parse with `float(ratio_str.replace('%',''))`.
- **Non-trading days**: On weekends/holidays, gsz is absent or stale (shows last trading day's data).
