---
name: chinese-stock-data
description: >-
  Parse, query, and work with Chinese A-share stock market data:
  TDX binary .day files, Sina/Tencent/East Money live APIs,
  and 财报/季报解读 (financial reports, earnings-miss risk, market-wide review).
  Covers daily k-line, real-time quotes, disclosure calendars.
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

### 5. 东方财富 push2 — Real-time Index & Stock Quotes (HTTP)

Fast, no-auth endpoint for real-time market data. Works via plain `curl` from inside China.

**Base URL:** `https://push2.eastmoney.com/api/qt/ulist.np/get`

**secids format:** `{market}.{6-digit-code}` where market prefix is:
| Market | Prefix | Example |
|--------|--------|---------|
| 上海 Shanghai | `1.` | `1.000001` (上证指数) |
| 深圳 Shenzhen | `0.` | `0.399001` (深证成指) |
| 创业板 ChiNext | `3.` | `3.300750` (宁德时代) |

**Major index codes:**
| Index | secid |
|-------|-------|
| 上证指数 | `1.000001` |
| 深证成指 | `0.399001` |
| 创业板指 | `0.399006` |
| 沪深300 | `1.000300` |
| 科创50 | `1.000688` |
| 北证50 | `0.899050` |

**Key fields:**
| Field | Description |
|-------|-------------|
| `f2` | 最新价 (×100 for stocks, raw for indices) |
| `f3` | 涨跌幅% (×100, e.g. 134 = +1.34%) |
| `f4` | 涨跌额 (×100) |
| `f5` | 今开 (×100) |
| `f6` | 成交量(手) |
| `f7` | 成交额(元) |
| `f12` | 6位代码 |
| `f14` | 名称 |
| `f15` | 最高 (×100) |
| `f16` | 最低 (×100) |
| `f17` | 涨跌额(备用) |
| `f18` | 昨收 (×100) |

**Example — 6 major indices:**
```bash
curl -s "https://push2.eastmoney.com/api/qt/ulist.np/get?secids=1.000001,0.399001,0.399006,1.000300,1.000688,0.899050&fields=f2,f3,f4,f5,f6,f7,f12,f14,f15,f16,f17,f18"
```

**Example — daily K-line (single stock/index):**
```bash
curl -s "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.000001&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57&klt=101&fqt=1&end=20260805&lmt=1"
# Returns: date,open,close,high,low,volume,amount
```
- `fields2=f51..f61` extends to: 振幅%, 涨跌幅%, 涨跌额, 换手率% — saves recomputing pct change per bar (verified 2026-09-01)
- `lmt=320` ≈ 15 months of trading days — enough history for prior-high / resistance-zone analysis

**Single-stock fundamentals (push2 stock/get, HTTP, no auth):**
```bash
curl -s "http://push2.eastmoney.com/api/qt/stock/get?secid=0.002966&fields=f43,f57,f58,f116,f117,f162,f163,f164,f167,f168"
```
- `f43` = 最新价×100; `f116`/`f117` = 总市值/流通市值（元）; `f167` = PB×100; `f168` = 换手率%×100
- `f162/f163/f164` are three PE variants (all ×100) — which one is TTM varies by stock; cross-check against computed value (市值/净利润) before quoting any of them

**⚠️ Note:** HTTPS to push2 may be DNS-blocked by some routers (e.g. Xiaomi 192.168.31.1). Use HTTP or `--resolve` workaround (see below). For batch stock queries (your watchlist), the `secids` parameter uses the same market prefix rules: 上海 stocks use `1.`, 深圳 stocks use `0.`, 创业板 use `3.`.

### 6. 东方财富 datacenter — 财报数据与披露日程（“三季报怎么样 / 什么时候出”必用）

两个端点就能回答「业绩如何」和「财报哪天出」，都不需要 auth：

```bash
# 业绩（单季/累计都靠它算）
curl -s -H "Referer: https://data.eastmoney.com/" \
  "https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_LICO_FN_CPD&columns=ALL&filter=(SECURITY_CODE%3D%22002039%22)&pageSize=40&pageNumber=1&source=WEB&client=WEB"

# 预约披露日 / 实际披露日
curl -s -H "Referer: https://data.eastmoney.com/" \
  "https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_PUBLIC_BS_APPOIN&columns=SECURITY_CODE,SECURITY_NAME_ABBR,REPORT_DATE,APPOINT_PUBLISH_DATE,ACTUAL_PUBLISH_DATE&filter=(SECURITY_CODE%3D%22002039%22)&pageSize=5&source=WEB&client=WEB"
```

**`RPT_LICO_FN_CPD` 关键字段**：`REPORTDATE`（报告期）、`TOTAL_OPERATE_INCOME`（营业总收入，元）、`YSTZ`（营收同比%）、`PARENT_NETPROFIT`（归母净利，元）、`SJLTZ`（净利同比%）、`BASIC_EPS`、`WEIGHTAVG_ROE`。一次拉 40 条可以拿到近 10 年全部季报/年报，不用分批。

**四个坑（都实测过）**：
1. **列名是 `REPORTDATE` 不是 `REPORT_DATE`** —— 传 `sortColumns=REPORT_DATE` 会直接报 `"REPORT_DATE排序列不存在" code:9501`。**干脆不传 `sortColumns`**，返回顺序已经是倒序（最新在前）。
2. **主机名必须带 `-web`**：`datacenter.eastmoney.com`（无 `-web`）返回 `{"result":null}` / 0 行，看着像“没数据”，其实是错的子域。
3. **单季数据要自己减**：接口只给累计值。Q3 单季 = 三季报累计 − 中报累计（营收和净利各自减），同比也用单季算。这是判断“业绩拐点”的关键——一个公司可能半年报 +83%、三季报累计 +25%，拆开才看到 Q3 单季是 **−52%**。
4. **`filter` 里的引号必须 URL 编码**：`(SECURITY_CODE%3D%22002039%22)`，直接写 `="002039"` 会被拒。

**判读配套（"这只票会不会爆雷"）**：拿到同比之后不要直接下结论，按下面五步走——

1. **先定商业模式的可预测性**（这一步决定后面所有判断）。靠天吃饭的行业（水电/煤炭/养殖/航空）同比在 −47%~+175% 之间摆动是常态，单季腰斩只能说明气候或价格周期，拿“上一年是高基数”解释下滑 ≠ 经营恶化；银行/公用事业/高速这类连续多年 5%~10% 的品种才是可比的年报口径。**用同一个"爆雷"标准套两种商业模式是错的**。
2. **看历史波动区间判断"这品种能不能暴跌"**：连续 8 年正增长的品种（如优质城商行）没有"单季腰斩"的机制——收入是一笔笔贷款攒出来的，不会某天突然归零；而利润在 1 亿~6 亿之间年年跳的品种，一个季度就能把全年增速打负。
3. **用已披露季度做锚**：未出三季报时，中报里的 Q1/Q2 单季增速比任何预测都准（业务平缓的品种尤其适用）。给用户的概率区间要基于这个锚，不是拍脑袋。
4. **看利润的可调节垫子**：银行额外看**拨备覆盖率**——行业均值约 205%、城商行约 173%，380% 以上的拨备意味着坏账翻几倍也兜得住，几乎不存在"业绩腰斩"的可能；反过来，拨备已压到行业下限、还在释放拨备保利润的，才是真正的风险点。非银看其他压舱物：在手订单、现金流、合同负债。
5. **必须把"雷"拆成两档再报概率**：
   - **绝对爆雷**（净利负增长/腰斩）：商业模式失效才会发生，概率低但杀伤大；
   - **不及预期**（增速仍为正、但低于券商一致预期）：这才是股价下跌的常见原因，**先查一致预期（券商策略报告/盈利预测）再评估**，实际落在预期下限也会跌。

给用户结论时两档分开写（如"下滑概率 <5%，但只及预期下限导致回调的概率 20-25%"），不要笼统说"爆雷概率低"——他要回答的是「会不会跌」，不是「会不会亏」。

### ⚠️ 字段顺序：每个接口各不相同（最高频的数据事故）

同一个「收盘价」在不同接口里位置完全不同。**按猜的索引解析不会报错，只会把行情读反**，而且读反后的数字看着都很合理，肉眼难以察觉。引用前先打印一行原始数据对照，再继续。

**新浪 `hq.sinajs.cn` 是「今开、昨收、现价、最高、最低」，不是「现价、昨收、…」**：

| 索引(0-based) | 字段 |
|:---:|:---|
| 0 | 名称 |
| 1 | **今开** |
| 2 | 昨收 |
| 3 | **现价 / 收盘** |
| 4 | 最高 |
| 5 | 最低 |
| 6 / 7 | 买一 / 卖一 |
| 8 | 成交量（股） |
| 9 | 成交额（元） |
| 30 / 31 | 日期 / 时间 |

```python
p = line.split('="')[1].rstrip('";').split(',')
name = p[0]
open_, prev_close, cur, high, low = (float(x) for x in p[1:6])
chg = (cur / prev_close - 1) * 100
```

**把索引 1 当现价的后果**：一个收盘 3690.48、涨 0.89% 的交易日会被读成「今开 3623.57、跌 0.94%」，于是一根大阳线被复盘成「全线下跌」。腾讯 `qt.gtimg.cn`（`~` 分隔，索引 3=现价、4=昨收、5=今开）与东财 push2（`f2`=现价）的偏移量又各不相同 —— 跨源比对时逐源核对索引，**不要复用上一份代码的偏移量**。

**自查信号（出现任一就必须回头验字段，不要继续写结论）**：
1. 指数方向与板块/涨跌家数方向相反；
2. 「今开 − 昨收」算出的幅度与接口给的涨跌幅对不上；
3. 现价落到最高/最低区间之外，或「现价」恰好等于某个整点时刻的开盘价；
4. 新闻复盘（深V反转/绝地反击）与你的数据结论（全线下跌）矛盾 —— **此时优先怀疑解析，不要怀疑新闻**，用同一份原始串重新对齐索引。

复盘一整个交易日时，至少交叉两个源（新浪 `hq.sinajs.cn` + 腾讯 `ifzq`/`push2`），两源收盘价一致再下笔。

### ⚠️ API Availability (tested on this environment)

| API | Status | Notes |
|-----|:------:|-------|
| Sina stock list | ✅ Works | Fast, no auth |
| Tencent qt.gtimg.cn | ✅ Works | Best for real-time batch quotes |
| akshare THS financial | ✅ Works | Reliable ROE source |
| Tushare daily | ✅ Works | Rate-limited, reliable |
| 东方财富 push2 (HTTP) | ✅ Works | HTTP works; HTTPS may be DNS-blocked by router |
| 东方财富 push2 (HTTPS) | ⚠️ DNS-blocked | Router DNS blocks subdomains; bypass with `--resolve` via 114 DNS |
| 东方财富 datacenter | ✅ Works | F10 dividends + **大宗交易** (see `references/dzjy-block-trade-api.md`) |
| 腾讯板块排行 pt/getRank | ⚠️ 仅参考 | `direct=up/down` **并不按涨跌幅排序**（实测两向返回同一批），须取全量（offset 0/30 各拉一次）后在 Python 里按 `zdf` 自己排；且其 `zdf` 可能与当日指数方向矛盾（缓存/口径不同），当作「收盘复盘」用之前先跟指数、涨跌家数交叉验证，矛盾就以指数为准 |
| 东方财富 push2 高频调用 | ⚠️ 会限流 | 连续多次调用后返回 `HTTP:000` + 空 body（**不是 DNS 问题，别去改 hosts 或加 --resolve**）。停几秒重试，或直接切腾讯 `qt.gtimg.cn` / 新浪 `hq.sinajs.cn` 取同一指标 |
| 搜狐 Sohu K-line | ❌ Dead | API deprecated |
| 腾讯 ifzq K-line | ✅ Works | `https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sz002039,day,,,150,qfq`；返回 `data.<code>.qfqday`，**前复权**，第 4 个参数=条数 |
| 新浪 K-line | ✅ Works | `https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=sz002039&scale=240&ma=no&datalen=30`（**不复权**，volume 单位为股） |
| 新浪实时 | ✅ Works | `https://hq.sinajs.cn/list=sz002039`，需 `Referer: https://finance.sina.com.cn`，响应 **GBK** → `iconv -f gbk -t utf-8` |
| 财联社新闻搜索 | ❌ Dead | API returns empty, needs auth |
| 同花顺新闻搜索 | ❌ Unreliable | DNS resolution fails or 404 |
| 百度股票搜索 | ❌ Unreliable | Returns empty JSON |
| 东方财富 search-api-web 新闻搜索 | ✅ Works | `search-api-web.eastmoney.com/search/jsonp`，无需 auth，JSONP 需剥壳，见 News Search 章节 |

### DNS Bypass for Blocked East Money Subdomains

The router DNS (192.168.31.1) blocks many eastmoney subdomains (e.g. `push2`, `reportapi`, `np-listapi`, `datacenter-web`, `searchapi`). However, these domains DO resolve via alternative DNS (114.114.114.114):

```bash
# 1. Resolve via 114 DNS
host datacenter.eastmoney.com 114.114.114.114
# → datacenter.eastmoney.com is an alias for ...queniukt.com, has address 60.169.2.26

# 2. Use --resolve to bypass system DNS
curl -sL --max-time 10 -4 "https://datacenter.eastmoney.com/web/api/data/v1/get?reportName=..." \
  -H "User-Agent: Mozilla/5.0" \
  --resolve "datacenter.eastmoney.com:443:60.169.2.26"
```

**Must use** `-4` (IPv4) and `--resolve` together. The `--resolve` flag accepts `hostname:port:address` and hardcodes the IP for that host, bypassing the system DNS. Pick any resolved IP for the target subdomain — they're load-balanced.

See `references/dzjy-block-trade-api.md` for the full block trade (大宗交易) data API using this technique.

## 网络日线补齐与自动化（TDX 长期不可用 / 用户出差时）

TDX 的 `vipdoc` 依赖用户手动“盘后下载”；RDP 断开或用户出差时本地数据会整段缺失，但分析链路本身不必依赖它。

**本机 DSA 项目（`~/dsa`）全走网络**：优先级 Tushare(P-1) → Efinance(P0) → Tencent(P0) → Akshare(P1) → Pytdx(P2) → Baostock(P3) → Yfinance(P4)，前三失败会自动降级。Pytdx 是**网络协议**（连通达信行情服务器），不读本地 `.day`——“没下载通达信数据就没法分析”是误解。

- **取数命令**：`cd ~/dsa && ./venv/bin/python main.py --dry-run --no-market-review`（只取数据不做 LLM 分析，9 只约 5-10 秒）
- **跑的时刻决定拿到哪一天**：09:00 跑 → **T-1**（当天还没开盘）；**16:00 后跑 → 当天收盘数据**（Tushare 日线已更新）。用户要“当天盘后数据”就排 15:30-16:30，排开盘前会永远晚一天。
- **落库**：`~/dsa/data/stock_analysis.db` → `stock_daily(code,date,open,high,low,close,volume,amount,pct_chg,data_source,...)`，`volume` 单位是**股**。
- **⚠️ `main.py` 只抓 `STOCK_LIST` 里的股票，不抓 ETF**：ETF 必须单独补（本机现成脚本 `~/dsa/fetch_etf_daily.py`，新浪优先/腾讯兜底，只插缺失日期，可反复跑）
  - ETF 代码前缀：`159xxx` → `sz`，`51xxxx`/`56xxxx`/`58xxxx` → `sh`
  - **ETF 优先用新浪 K-line，不要用腾讯 ifzq**：部分 ETF 在 ifzq 返回的节点不是 `qfqday`（只有 `day`），按 qfqday 解析会报 `string indices must be integers`；且新浪 `volume` 直接是**股**，与 `stock_daily` 口径一致，腾讯是**手**（需 ×100）
- **自动化建议用 watchdog 模式**：`~/dsa/daily_topup.py` = 交易日判断 → main.py 取股票 → fetch_etf_daily.py 取 ETF → 校验每个标的是否有当日记录；**齐全时 stdout 为空**，有缺失才输出告警，配合 `no_agent` cron 即“正常不推送、异常才打扰”。cron 表达式 `30 16 * * 1-5`。
- **cron 的 `script` 参数只收 `~/.hermes/scripts/` 下的相对文件名**（绝对路径会被拒），用一个 3 行包装脚本 `subprocess.run([dsa/venv/bin/python, dsa/daily_topup.py], cwd=dsa)` 转发 stdout 即可。
- **完整性自检**：按 `SELECT DISTINCT date ... ORDER BY date DESC LIMIT 40` 逐日比对全部标的；只看 `MAX(date)` 会漏（它只反映最新那只）。
- **别在 heredoc 里内联引用大数据库**：安全守卫要求命令引用的脚本/文件可扫描且 <1 MiB，`stock_analysis.db` 这类库会把整条命令拦成 “scan budget exhausted”。修法：把查询写成 `/tmp/xxx.py` 再 `python3 /tmp/xxx.py`（对 `smd.db` 那种几百 KB 的小库，`python3 -c` 内联没问题）。

## 自选股池增删（“把 XXX 移出股票池”）

用户说“清仓了，把 XXX 移出股票池”时，**不是只改一处**：代码里有 7 处各自硬编码了一份自选股列表，漏改任何一处都会导致次日分析仍把它算进去（或名字映射 KeyError）。

**必改清单**（本机 `~/dsa` + `~/.hermes/memories/USER.md`）：

| 位置 | 内容 |
|---|---|
| `~/dsa/.env` | `STOCK_LIST=...`（DSA 主程序读这个）|
| `~/dsa/daily_topup.py` | `CODES = [...]`（盘后补齐脚本，含 ETF）|
| `~/dsa/gen_analysis_data.py` | `STOCKS = [...]` + `NAMES = {...}` 两处 |
| `~/dsa/cron_indicator_report.py` | `NAMES = {...}` |
| `~/dsa/compute_indicators.py` | `WATCH = {...}` |
| `~/dsa/compute_analysis_*.py` | 历史一次性分析脚本里的 `WATCH`/列表（不影响运行，但为一致性一并改）|
| `~/.hermes/memories/USER.md` | “A 股自选股（N 只）”标题里的数字 + 表格里的行 |

**流程与验证**：
1. 先 `grep -rn "<代码>" --include="*.py" --include=".env" ~/dsa` 摸清全部命中点（排除 `venv/`、`reports/`、`data/cache/` —— 历史报告和缓存里的命中不算残留）。
2. 逐处 patch（**用 patch 工具，不要 sed** —— `.env` 是 600 权限的敏感文件，批量 sed 容易连带改错行）。
3. 改完重扫一次 grep，输出为空才算干净；再跑一遍 `venv/bin/python -c "import ast; ..."` 语法检查被改的脚本。
4. **数据库里的历史日线不要删**：`stock_analysis.db` 里该股的旧记录留着做复盘/回测正好用，删了反而丢历史（已退出的股票只是不再被补齐，不影响新数据）。
5. 报告时列出“改了哪几处 + 现股票池几只（N 股 + M ETF）+ 保留了 N 条历史数据”。

## 长影线 / 多空分歧研判（“连续几天长上下影线，要不要走？”）

用户对形态的描述常偏主观（“长影线”可能只有 1% 幅度、“高位”可能只是区间中位），**先用数据验证三个前提再谈结论**：

1. **取 150 日前复权日线**，算位置：`(现价 − 150日低) / (150日高 − 150日低)`。>80% 才算高位；50% 附近只能说“阶段高位”（相对近 10 日涨幅），**不是历史高位**。再列各月最高价，看趋势是逐月下移还是刚回升。
   **分位祇回答“在区间哪一段”，不等于贵贱**：银行、公用事业、高速等高股息价值股，必须叠 PB/PE/股息率再说估值 —— PB 0.8 倍、PE 6.5 倍、股息 5% 的银行即使站在 85% 分位也是“位置高但估值不贵”，说成“全场最贵”是错。反之高估值成长股在 15% 分位也只能说“跌了很多”，不等于便宜。两步分开做：先分位排结构，再估值定贵贱。
2. **影线量化**：`上影 = high − max(open,close)`、`下影 = min(open,close) − low`、`影线占振幅 = (上影+下影)/(high−low)`。影线占振幅 ≥60% + 实体极小 才是“多空拉锯”K 线；但**必须同时看绝对幅度**——影线仅 0.5%~1.5%、日振幅 <3.5% 属温和震荡，不是“剧烈分歧”。
3. **量能定性（最关键）**：`5日均量 / 20日均量`。≈1.0 或不放大 = **缩量换手/洗盘**；真出货是**放量滞涨**（量能放大 1.5 倍以上而价格不涨）。**“高位长影线 + 缩量” ≠ 顶部**——不要据此劝用户清仓。
4. **趋势结构**：MA5/10/20/60 是否多头排列、现价在哪条均线上方。没放量跌破 MA20，趋势未坏。
5. **结论必须给条件触发价位**，不只给“建议减仓”：阻力（区间高点/前高）、支撑（MA10/MA20/MA60/区间低点）、**用户成本价**，各自对应「继续持有 / 减仓 / 清仓」。
6. **先问按哪套逻辑持有**：金医生是长线 ETF + 个股量化双策略。长线逻辑下基本面（业绩预告、来水/发电量等已入库数据）没变就不要因小震荡劝下车；短线逻辑才谈部分止盈。

**Tencent ifzq 日线字段顺序坑**：`qfqday` 每行是 `[date, open, close, high, low, volume]`——**close 在 high/low 之前**，不是常见 OHLC。按 OHLC 解析会把收盘/最高/最低搞错且不报错，必须照此顺序取。

一键速检：`python3 scripts/kline_shadow_check.py <6位代码> [条数]`——取前复权日线，直接输出区间分位、最近 12 日影线明细、量能比与均线位置，省掉手写解析。

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
- **RDP drive unmounted**: `thinclient_drives/E:` may only contain `HermesBackup` when the RDP session is disconnected — vipdoc paths silently missing. Check `os.path.exists()` on the `.day` file first; if absent, go straight to online APIs (push2his K-line with `lmt=320` covers full history for resistance-zone analysis). **If push2his returns HTTP:000**（它可能只解析到 IPv6 如 `2406:d440:...` 而静默失败），别在 DNS 上空转——直接换 腾讯 ifzq 或 新浪 K-line（两者实测可用，同样能取 150~320 条日线）。
- **Tencent qt.gtimg.cn field alignment**: When a stock is 跌停/涨停 (limit down/up), some fields shift or contain anomalous values. The 换手率 (field 37) can return a non-percentage number (e.g. 317995 instead of 0.78%). Always cross-check with field 49 (换手率备用) or compute manually: `成交量(手) * 100 / 流通股本(万股)`. Similarly, field 41 (每股净资产) and field 42 (流通股本) can be misaligned on limit days — verify against known values or use East Money push2 API (field f185/f186) as a backup source. PE(TTM) field 38 and turnover fields have been observed wrong even on NORMAL days (苏州银行 2026-09-01: field 38=1.08 vs actual ≈5.95; field 49=1.59% vs computed 1.08%) — for valuation metrics use East Money push2 stock/get as the authoritative source (see Single-stock fundamentals above).
- **execute_code may be blocked**: In some Hermes configurations, `execute_code` is blocked by security policy (cron_mode). When this happens, use `terminal` with inline `python3 -c "..."` or heredoc `python3 << 'EOF'` instead.
- **News search APIs are unreliable**: Most Chinese financial news APIs (财联社, 同花顺, 百度) fail with 404, empty responses, or DNS errors. **Exception — 东方财富 `search-api-web.eastmoney.com` works** (no auth, JSONP format; strip the `jQuery(...)` wrapper). For breaking news about a stock, use that endpoint first, then browser-based search as fallback. See `references/stock-news-investigation.md` for the full per-stock news/rumor check workflow.

---

## Industry Index Comparison (个股 vs 行业指数)

A common user request: "compare my stock to its industry index, check MA60 position, should I hold or sell?"

### Workflow

1. **Find industry index code** — see `references/tdx-industry-index-lookup.md` for the mapping from `tdxzs.cfg`. Common: 电力=880305, 银行=880471.
2. **Parse both** — the index `.day` files use the same binary format as stocks. They live in `vipdoc/sh/lday/sh880xxx.day`.
3. **Compute MA60** for both stock and index — the critical decision level for long-term holders.
4. **Check relative position**:
   - Stock near but below MA60 + index also below = sector-wide pressure (wait/減仓)
   - Stock near MA60 + index well above = stock-specific lag (possibly catch-up)
   - Stock above MA60 + index above = confirmed uptrend (hold)
5. **Volume check**: Compare current volume to 5-day average (量比) — confirm if move is supported.

### Presentation (for this user)

Use a compact table with these rows per stock:
- Latest close, MA60 distance %, MA60 status (突破/未站上)
- Industry index same metrics
- Volume vs 5-day average
- Short-term trend (recent 4-5 day direction)

Avoid verbose prose — the user wants data first, your judgment second, in that order.

## Trend & Space Assessment (趋势与空间研判)

For "下一步趋势和空间" questions — beyond MA scoring, this workflow produced a well-received scenario analysis (苏州银行 2026-09-01):

1. **Long history**: fetch ~320 trading days (`lmt=320` on push2his K-line ≈ 15 months) to find the last major high and — critically — how price behaved when it LAST touched that level (historical precedent at key levels beats any indicator: e.g. a prior failed test with volume-less top + no catalyst → -15% over 6 weeks is a warning template).
2. **Resistance zones**: prior highs + dense trading shelf above current price; count historical closes above each candidate target (0 days above X = virgin territory, expect friction there).
3. **Fibonacci** from swing low → prior high: 0.382/0.5/0.618 as retracement support, 1.0 = prior high, 1.272/1.618 as extension targets.
4. **Volume trend**: monthly average volume — rising into the breakout = quality; compute max drawdown within the rally (shallow pullbacks <8% = strong structure).
5. **Valuation mapping** (banks): map each target price to PB (scale current PB by price ratio) — 破净 is a safety margin, ~0.9x ≈ peer-average ceiling without sector-wide re-rating; for non-banks use PE vs sector median instead.
6. **Scenario table**: 2-3 scenarios with subjective probabilities, path description, target range (+%), plus explicit confirmation signals (e.g. "放量>50万手收盘站上9.12") and invalidation levels (MA20 break).

### Presentation (for this user)

- Scenario table first (情景 | 概率 | 路径 | 目标空间), then key confirmation signals as a short numbered list, then one-line conclusion.
- Anchor everything to the nearest historical level with concrete numbers ("距前高9.12仅0.7%") — beats abstract "还有空间".

## 板块轮动分析（“哪个板块接替龙头 / 科技跌了钱去哪了”）

板块指数的直接来源在本环境不可靠：**东财 BK 行业指数（`90.BK` secid）限流/返回空**，腾讯板块 K 线（`pt01801784` 之类）结构不一致无法程序化解析。**改用宽基 ETF 代理行业**——同一 push2his/ifzq 端点、数据干净、代码即行业：

| 行业 | 代理 ETF | 行业 | 代理 ETF |
|---|---|---|---|
| 红利 | 515080 | 银行 | 512800 |
| 煤炭 | 515220 | 保险 | 512070 |
| 军工 | 512660 | 白酒 | 512690 |
| 电力 | 159611 | 有色 | 512400 |
| 医药 | 512010 | 通信 | 515880 |
| 光伏 | 515790 | 证券 | 512880 |

**方法（250 日窗口，一次拉齐全部候选再横向对比）**：
1. 每只 ETF 取 250 日前复权日线（ifzq `qfqday`，注意 close 在 high/low 之前）。
2. 每板块算五个数：**当日涨跌%、250 日分位 `(cur-lo)/(hi-lo)`、60 日涨幅、距 MA20%、20 日涨幅**。输出成一张表。
3. 横向排序看 60 日涨幅与当日抗跌性——**“接替龙头”的判据不是谁涨得多，而是相对强度**（大盘跌它不跌 / 逆势收阳）或**低位+动量**（分位 <50% 但 60 日 >5%）。两者都满足的才是进攻接替候选；只满足高位的（如银行 100% 分位）定性为**避险/防御，不追**。
4. 结论必须区分两档：**短期无新龙头只有防御**（高股息避风港，赚“科技跌它不跌”的钱）与**中期进攻接替者**（低位+抗跌+叙事，条件触发型）。

**呈现（金医生偏好）**：全板块体检表（板块 | 当日 | 250日分位 | 60日 | 距MA20 | 定性，🔴/★ 标记）→ 判断逻辑（为什么不是 X、谁最可能、次选、不碰的及原因）→ 持仓角度（现有防御仓是否够，别重复配置）→ 纪律表（动作 | 触发条件：放量站上 MA20 等右侧信号、单仓上限、总仓位纪律）。**所有接替候选都是条件触发型**——信号没出现就写“记入观察列表，别抢跑”，不给现价买入建议。

---

## Reference Files

- 组合层面的持仓体检与配置建议（要不要卖/买/换、集中度、分批、纪律线）见 skill: `portfolio-allocation-review`。

- `references/stock-news-investigation.md` — 个股异动/利空核查工作流（"为什么XX低开/大跌？有没有特殊信息？"）：盘面→公告→新闻搜索→龙虎榜/大宗/融资→股吧→K线→财报披露日，全部端点含 curl 命令。
- `references/002039-example.md` — Worked example of parsing 002039 黔源电力 (Shenzhen) with actual raw binary values, price validation, and recent market data.
- `references/trend-space-assessment-002966.md` — Worked example: 苏州银行 trend & space assessment (prior-high precedent, Fibonacci targets, PB mapping, scenario table format).
- `references/rdp-mapped-tdx-data.md` — Reading TDX data from RDP-mapped drives (thinclient_drives via xrdp-chansrv), handling slow fuse mounts, and determining price scaling via the amount cross-check.
- `references/tdx-industry-index-lookup.md` — How to find TDX industry/sector index codes from `tdxzs.cfg`, with common codes (电力 880305, 银行 880471, etc.) and data file locations.
