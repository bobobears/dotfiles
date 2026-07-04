# 大宗交易 (Block Trade) API — East Money Datacenter

Full reference for querying A-share block trade (大宗交易) data via East Money's datacenter API, including DNS bypass for blocked subdomains.

## DNS Bypass

The router DNS (192.168.31.1) blocks most eastmoney subdomains. Use `--resolve` to bypass:

```bash
# Resolve via 114 DNS first
host datacenter.eastmoney.com 114.114.114.114
# Takes a note of the IPv4 address (e.g. 60.169.2.26, 60.169.2.27)

# Then curl with --resolve + -4
curl -sL --max-time 10 -4 "https://datacenter.eastmoney.com/..." \
  -H "User-Agent: Mozilla/5.0" \
  --resolve "datacenter.eastmoney.com:443:60.169.2.26"
```

**Requirements:**
- `-4` (IPv4) — without this curl defaults to IPv6 which fails
- `--resolve "hostname:port:ip"` — hardcodes DNS bypass
- Any resolved IP works; they're load-balanced

## API Endpoint

```
GET https://datacenter.eastmoney.com/web/api/data/v1/get
```

### Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `reportName` | `RPT_DATA_BLOCKTRADE` | The block trade report |
| `columns` | `ALL` | Return all fields |
| `pageNumber` | `1` | Page number (1-indexed) |
| `pageSize` | `50` | Records per page (max ~50) |
| `sortTypes` | `-1` | -1 = descending |
| `sortColumns` | `TRADE_DATE` | Sort by trade date |
| `source` | `WEB` | Data source |
| `client` | `WEB` | Client type |
| `filter` | `(SECURITY_CODE="002966")` | URL-encoded filter |

### Filter Syntax

The `filter` parameter uses URL-encoded parentheses + quoted strings:

```
filter=(SECURITY_CODE=%22002966%22)
# decodes to: (SECURITY_CODE="002966")

# Date range filter:
filter=(TRADE_DATE>='2026-07-01'%20AND%20TRADE_DATE<='2026-07-03')
```

### Complete Query Example

```bash
# Block trades for stock 002966
curl -sL --max-time 10 -4 \
  "https://datacenter.eastmoney.com/web/api/data/v1/get?\
reportName=RPT_DATA_BLOCKTRADE&\
columns=ALL&\
pageNumber=1&\
pageSize=50&\
sortTypes=-1&\
sortColumns=TRADE_DATE&\
source=WEB&\
client=WEB&\
filter=(SECURITY_CODE=%22002966%22)" \
  -H "User-Agent: Mozilla/5.0" \
  --resolve "datacenter.eastmoney.com:443:60.169.2.26" \
  | python3 -m json.tool
```

## Response Fields

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| `SECUCODE` | str | `"002966.SZ"` | Exchange-qualified code |
| `SECURITY_CODE` | str | `"002966"` | Plain 6-digit code |
| `SECURITY_NAME_ABBR` | str | `"苏州银行"` | Stock name |
| `TRADE_DATE` | str | `"2026-07-02 00:00:00"` | Trade date |
| `DEAL_PRICE` | float | `6.35` | Block trade price (元) |
| `PREMIUM_RATIO` | float | `-0.111888111888` | Premium ratio (decimal; negative = discount) |
| `DISCOUNT_RATIO` | float | `-9.929078014184` | Discount ratio (%); ~-10 means ~10% below market |
| `DEAL_VOLUME` | int | `326100` | Volume in shares (股), not 手 |
| `DEAL_AMT` | int | `2070700` | Total amount in 元 |
| `CLOSE_PRICE` | float | `7.15` | Same-day closing price |
| `PRE_CLOSE_PRICE` | float | `7.05` | Previous trading day's closing price |
| `BUYER_NAME` | str | `"国联民生证券股份有限公司苏州南天成路证券营业部"` | Buyer brokerage |
| `SELLER_NAME` | str | `"国联民生证券股份有限公司苏州南天成路证券营业部"` | Seller brokerage |
| `BUYER_CODE` | str | `"10000351806"` | Buyer institution code |
| `SELLER_CODE` | str | `"10000351806"` | Seller institution code |
| `TURNOVER_RATE` | float | `0.006588776408` | Turnover ratio (decimal; ×100 = %) |
| `DAILY_RANK` | int | `19` | Rank among block trades that day |
| `TRADE_UNIT` | str | `"4"` | Trade unit type |
| `PREMIUM_TURNOVER` | int | `0` | Premium portion of turnover (元) |
| `DISCOUNT_TURNOVER` | int | `2070700` | Discount portion of turnover (元) |
| `UNLIMITED_A_SHARES` | int | `4395480643` | Circulating A-shares |
| `TOTAL_SHARES` | int | `4470662011` | Total shares outstanding |
| `FREE_SHARES_RATIO` | float | `0.007418983872` | Ratio of block trade volume to circulating shares |
| `TOTAL_SHARES_RATIO` | float | `0.007294221733` | Ratio of block trade volume to total shares |
| `CHANGE_RATE` | float | `1.4184` | Stock price change rate (%) |
| `INDEX_CLOSE` | float | `9301.0657` | Index close (likely the corresponding index) |
| `QUOTES_CODE` | str | `"002966.0"` | Internal quotes code |

## Interpretation

### Same-Brokerage Trades (对倒交易)

When `BUYER_NAME == SELLER_NAME` and the same branch office, this is an **internal transfer** (对倒/账户间转让). Common patterns:
- Same brokerage, same branch → almost certainly internal book transfer
- Different brokerages → genuine market block trade between independent parties

### Discount Analysis

Typical discount ranges:
- **-10%**: Near the regulatory max discount for block trades — often internal transfers
- **-5% to -10%**: Normal third-party block trades
- **0% to +3%**: Premium trades (buyer pays above market; rare)

### Pagination

Response contains `"pages"` (total pages) and `"data"` (records array). To fetch all pages, increment `pageNumber`:

```python
import json, urllib.request

def get_all_block_trades(code, ip="60.169.2.26"):
    base = f"https://datacenter.eastmoney.com/web/api/data/v1/get"
    all_records = []
    page = 1
    while True:
        url = f"{base}?reportName=RPT_DATA_BLOCKTRADE&columns=ALL&pageNumber={page}&pageSize=50&sortTypes=-1&sortColumns=TRADE_DATE&source=WEB&client=WEB&filter=(SECURITY_CODE=%22{code}%22)"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        # Set up DNS bypass
        import socket
        original_getaddrinfo = socket.getaddrinfo
        def bypass_dns(host, port, *args, **kwargs):
            if host == "datacenter.eastmoney.com":
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]
            return original_getaddrinfo(host, port, *args, **kwargs)
        socket.getaddrinfo = bypass_dns
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read())
            records = data.get("result", {}).get("data", [])
            if not records:
                break
            all_records.extend(records)
            total_pages = data.get("result", {}).get("pages", 0)
            if page >= total_pages:
                break
            page += 1
        finally:
            socket.getaddrinfo = original_getaddrinfo
    return all_records
```

## Related Reports

From the East Money detail page JS (`detailA.js`), other related report names on the same API:
- `RPT_DATA_BLOCKTRADE` — 大宗交易明细 (block trade details)

Other subdomains in the East Money ecosystem (mostly blocked, use DNS bypass):
```
np-listapi.eastmoney.com    → 101.226.30.11
datacenter-web.eastmoney.com → 117.66.50.22 (via 114 DNS)
graydatacenter.eastmoney.com → 60.169.2.26 (likely same as datacenter)
reportapi.eastmoney.com     → 61.129.129.105 (via 114 DNS)
```
