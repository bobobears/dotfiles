---
name: chinese-stock-data
description: >-
  Parse, query, and work with Chinese A-share stock market data from
  通达信 (TDX) binary formats (.day, .min, .eday). Covers daily k-line,
  minute-line, and extended daily data. Handles Shenzhen, Shanghai, and
  Beijing exchange stock codes.
---

# Chinese Stock Data (TDX / 通达信 Format)

## Data Sources

Chinese stock data typically lives under a `vipdoc/` directory in 通达信-based trading software (e.g. 华安证券通达信版, 东方财富, 同花顺).

**Multiple installations:** A user may have several TDX installations (e.g. `zd_hazq`, `zd_hazq_gm`, `华安证券通达信版`) on the same machine, each with `vipdoc/`. Data recency may differ — always check the one with the most recent data when querying current dates.

**Slow/remote-mounted drives:** If data sits on an RDP-mapped drive (`thinclient_drives/`), NFS, or CIFS mount, shell commands like `ls`, `find`, and `grep` can time out on large directories. Workaround: use Python's `execute_code` tool instead — `os.listdir`, `os.path.exists`, and direct `open()` + `struct.unpack` handle fuse mounts more reliably and avoid timeout issues entirely.

**Directory structure:**
```
vipdoc/
├── sz/           # Shenzhen 深圳 stocks (codes starting with 00, 30)
├── sh/           # Shanghai 上海 stocks (codes starting with 60, 68)
├── bj/           # Beijing 北交所 stocks (codes starting with 8)
├── ds/           # Futures/data services
├── ot/           # Other markets
└── cw/           # Financial reports (财务数据)

Each exchange has sub-directories:
├── lday/         # Daily k-line (日线) — primary use
├── eday/         # Extended daily data (扩展日线)
├── minline/      # Minute-level data (分钟线)
└── fzline/       #复权线 (adjusted data)
```

**File naming:** `sz<6-digit-code>.day`, e.g. `sz002039.day`

**Stock code prefix conventions:**
| Exchange | Prefix | Examples |
|----------|--------|---------|
| 深圳 Shenzhen | `sz` | 000001, 002039, 300999 |
| 上海 Shanghai | `sh` | 600000, 688001 |
| 北京 Beijing  | `bj` | 830799 |

---

## TDX .day Binary Format

Each `.day` file contains fixed-size records, one per trading day. Record size = **32 bytes**.

### C struct layout:
```c
struct tdx_day_record {
    int   date;       // YYYYMMDD (e.g. 20260622)
    int   open;       // Opening price * 1000
    int   high;       // Highest price * 1000
    int   low;        // Lowest price * 1000
    int   close;      // Closing price * 1000
    float amount;     // Total turnover (成交额) in yuan
    int   volume;     // Volume in shares (股)
    int   reserved;   // Reserved / unused
};
```

### ⚠️ Determine scaling before parsing

Prices may be stored as ×100 **or** ×1000 depending on the TDX installation. Cross-check using the `amount` field — it's a float in yuan, so you can verify:

```python
import struct

record_size = 32
with open("sz002966.day", "rb") as f:
    data = f.read()

num_records = len(data) // record_size

# Parse the most recent record to determine scaling
offset = (num_records - 1) * record_size
rec = data[offset:offset + record_size]
date_val, open_p, high_p, low_p, close_p, amount, volume, reserved = \
    struct.unpack("<iiiiifii", rec)

# Try both scalings — the one where amount ≈ close_scaled × volume is correct
for scale_factor in [100, 1000]:
    close_try = close_p / scale_factor
    expected_amount = close_try * volume  # amount in yuan
    if abs(amount - expected_amount) < 0.2 * amount:
        print(f"Using scale /{scale_factor} (error: {abs(amount - expected_amount)/amount:.1%})")
        SCALE = scale_factor
        break
```

### Python parsing with struct (after scaling is known):
```python
import struct

record_size = 32
SCALE = 100  # or 1000 — determined via check above

with open("sz002966.day", "rb") as f:
    data = f.read()

num_records = len(data) // record_size
for i in range(num_records):
    offset = i * record_size
    rec = data[offset:offset + record_size]
    date_val, open_p, high_p, low_p, close_p, amount, volume, reserved = \
        struct.unpack("<iiiiifii", rec)

    # Decode
    year   = date_val // 10000
    month  = (date_val % 10000) // 100
    day    = date_val % 100

    open_f   = open_p / SCALE
    high_f   = high_p / SCALE
    low_f    = low_p / SCALE
    close_f  = close_p / SCALE
    vol_hands = volume / 100.0   # 手 = shares / 100
```

### Field details:
- **date**: `int`, format `YYYYMMDD`. Only trading days (weekdays, excluding holidays) are present.
- **open/high/low/close**: `int`, actual price = stored_int / 1000. So `1971` → `1.971` yuan.
- **amount**: `float`, total yuan turnover for the day.
- **volume**: `int`, in **shares (股)**. Chinese convention is 手 (board lots) where 1手 = 100 shares. Divide by 100 for 手.
- **reserved**: `int`, typically 0. May contain extra data in some software versions.

### Byte order:
Little-endian (`<` in struct format string). The full format string is `"<iiiiifii"`.

---

## Query Patterns

### Find the last N records (most recent trading days):
```python
for i in range(max(0, num_records - 5), num_records):
    # ... parse as above ...
```

### Find a specific date:
```python
target_date = 20260622
for i in range(num_records):
    ...
    if date_val == target_date:
        # found it
```

### Search by date range:
```python
start, end = 20260601, 20260630
for i in range(num_records):
    ...
    if start <= date_val <= end:
        print(...)
```

---

## Common Calculations

### Price change vs previous trading day:
```python
# Sort records by date
records.sort(key=lambda r: r['date'])
for i in range(1, len(records)):
    prev_close = records[i-1]['close']
    curr = records[i]
    change_pct = (curr['close'] - prev_close) / prev_close * 100  # percent
```

### Average volume (recent N days):
```python
recent = records[-20:]
avg_vol = sum(r['volume'] for r in recent) / len(recent)
```

---

## Online API Sources for A-share Market Data

Beyond local 通达信 files, several online APIs are useful for real-time screening and financial data. The following multi-source pipeline works reliably from within China:

```
Sina (stock list) → Tencent (real-time quotes) → 同花顺/akshare (ROE) → Tushare (K-line trend)
```

### 1. Sina — Stock Code List

Get the full list of A-share codes (沪深两市):

```
GET https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeDataSimple
    ?page=1&num=10000&sort=symbol&asc=1&node={sh_a|sz_a}&symbol=&_s_r_a=page
```

- `node=sh_a` for Shanghai (60xxxx, 68xxxx), `node=sz_a` for Shenzhen (00xxxx, 30xxxx)
- Returns JSON array with `code`, `symbol`, `name`
- Exclude codes starting with `8` (北交所) and names containing `ST`
- Very fast, no auth required

### 2. Tencent (qt.gtimg.cn) — Real-time Quotes with Key Fields

Batch query up to ~100 stocks per request. 88-field response, `~`-delimited:

```
GET https://qt.gtimg.cn/q=sh600519,sz300750,sz002039
```

**Critical field indices** (0-based split by `~`):

| Index | Content | Example |
|:-----:|---------|---------|
| 1 | 股票名称 | 黔源电力 |
| 2 | 股票代码 | 002039 |
| 3 | 现价 | 18.78 |
| 4 | 昨收 | 19.03 |
| 5 | 今开 | 19.16 |
| 6 | 成交量(手) | 72161 |
| **44** | **流通市值(亿)** | 80.30 |
| 45 | 总市值(亿) | 80.30 |
| **46** | **量比** | 1.84 |
| 32 | 涨跌幅% | -1.31 |

**Performance**: ~5200 stocks in 55 batch calls of 100, ~16 seconds total with 0.2s delay between batches.

### 3. 同花顺 via akshare — ROE / Financial Data

```python
import akshare as ak

df = ak.stock_financial_abstract_ths(symbol="600519")
# Returns columns including: 净资产收益率, 净利润, 每股净资产, etc.
roe = df["净资产收益率"].iloc[0]  # latest period
```

- Data source: 同花顺 (THS), not East Money — works independently
- Reliable, ~0.3s per call
- Supports all A-share codes (no exchange prefix needed)

### 4. Tushare Pro — K-line Data for Trend Analysis

```python
import tushare as ts
pro = ts.pro_api("your_token")

ts_code = "002039.SZ"   # or "600519.SH"
df = pro.daily(ts_code=ts_code, start_date="20260501", end_date="20260626")
```

- Returns: `trade_date, open, high, low, close, vol, amount`
- Sort by `trade_date` ascending before analysis
- **Free tier rate limits**: 1 call/min per API, 200 total/min
- For full market data: `pro.daily_basic(trade_date="20260626", fields="ts_code,circ_mv,turnover_rate,pe,pb")`
  - Note: `volume_ratio` may not be available on free tier

### ⚠️ API Availability (tested on this environment)

| API | Status | Notes |
|-----|:------:|-------|
| Sina stock list | ✅ Works | Fast, no auth |
| Tencent qt.gtimg.cn | ✅ Works | Best for real-time batch quotes |
| akshare THS financial | ✅ Works | Reliable ROE source |
| Tushare daily | ✅ Works | Rate-limited, reliable |
| 东方财富 push2 | ❌ Blocked | Connection refused (region/network) |
| 东方财富 datacenter | ✅ Works | For F10 data / dividends |
| 搜狐 Sohu K-line | ❌ Dead | API deprecated |
| 腾讯 ifzq K-line | ❌ Bad params | API format changed |
| 新浪 K-line | ❌ Not found | Deprecated |

## Trend Analysis (均线趋势评分)

After acquiring K-line data (via Tushare or other source), score uptrend strength:

```python
def check_trend(closes):
    """closes = list of latest 20+ daily close prices, oldest first"""
    if len(closes) < 20: return False, {}
    
    cur = closes[-1]
    ma5  = sum(closes[-5:]) / 5
    ma10 = sum(closes[-10:]) / 10
    ma20 = sum(closes[-20:]) / 20
    
    score = 0
    if cur > ma5:  score += 20  # Above short MA
    if cur > ma20: score += 20  # Above medium MA
    if ma5 > ma10 > ma20: score += 25  # Bullish alignment
    elif ma10 > ma20: score += 10
    if closes[-1] > closes[-5]:  score += 15  # 5-day up
    if closes[-1] > closes[-10]: score += 10  # 10-day up
    
    return score, {
        "trend": "强势上升" if score >= 80 else 
                 "上升" if score >= 55 else
                 "震荡" if score >= 30 else "下跌趋势",
        "cur": cur, "ma5": ma5, "ma10": ma10, "ma20": ma20,
        "pct_5d": (cur/closes[-5]-1)*100,
        "pct_20d": (cur/closes[-20]-1)*100,
    }
```

## Complete Screening Pipeline

See `references/a-stock-screening-pipeline.md` for the full implementation: Sina → Tencent → akshare(ROE) → Tushare(K-line), with ST-filtering and final formatting. This covers the four-criteria screen (circulating market cap, volume ratio, uptrend, ROE) used in this environment.

---

## Pitfalls

- **File encoding**: Files are binary, not text. Never try to read them as UTF-8/GBK.
- **Price scaling**: Prices are stored as `int × N` where N varies by software version. N=1000 is common in older installations; N=100 is common in newer ones (e.g. 华安证券通达信 `zd_hazq_gm`). **Always verify with the `amount` cross-check** (see "Determine scaling before parsing" above) instead of guessing. If both scalings are ambiguous (rare edge case), check against a known market close price for a recent day.
- **Volume units**: Volume is in **shares**, not 手 (hands). Divide by 100 for 手 which is the standard Chinese market convention.
- **Date format**: `YYYYMMDD` as a plain integer. Do NOT parse as a string — use integer division: `year = date // 10000`.
- **Holidays**: Only trading days are stored. Weekends and Chinese holidays (Spring Festival, National Day, etc.) will have gaps in the sequence.
- **Stock code lookup**: Always prepend the exchange prefix (`sz`/`sh`/`bj`) when constructing the file path. The 6-digit code alone is not unique across exchanges.
- **Data recency**: The `.day` file is updated after each trading day's close (盘后数据). Check the file modification time to see if it's current.

---

## Reference Files

- `references/002039-example.md` — Worked example of parsing 002039 黔源电力 (Shenzhen) with actual raw binary values, price validation, and recent market data.
- `references/rdp-mapped-tdx-data.md` — Reading TDX data from RDP-mapped drives (thinclient_drives via xrdp-chansrv), handling slow fuse mounts, and determining price scaling via the amount cross-check.
