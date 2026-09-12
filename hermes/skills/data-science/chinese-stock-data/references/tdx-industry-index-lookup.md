# TDX Industry Index Lookup (通达信行业板块指数)

## How to Find Industry Index Codes

Industry/sector indices in TDX are stored under `vipdoc/sh/lday/` with the prefix `sh880xxx.day`.

### Step 1: Decode `tdxzs.cfg`

The mapping lives in `T0002/hq_cache/tdxzs.cfg` (GBK encoding, pipe-delimited):

| Field | Content |
|-------|---------|
| Col 0 | Index name (GBK Chinese) |
| Col 1 | Index code (e.g. `880305`) |
| Col 2 | Level (3=region, 2=industry, etc.) |
| Col 3 | Sub-level |
| Col 4 | Sub-sub-level |
| Col 5 | Sort order / internal code |

### Python extraction:

```python
with open('T0002/hq_cache/tdxzs.cfg', 'rb') as f:
    for line in f.read().decode('gbk', errors='replace').split('\r\n'):
        parts = line.split('|')
        if len(parts) >= 2:
            name, code = parts[0], parts[1]
            # filter by keyword
```

### Common Industry Codes (this environment)

| Code | Index Name | Note |
|------|-----------|------|
| 880305 | 电力 (Power) | 传统电力股 |
| 880308 | 新型电力 (New Power) | 新型电力系统 |
| 880753 | 绿色电力 (Green Power) | 新能源发电板块 |
| 880471 | 银行 (Banking) | 银行全行业 |
| 880875 | 中小银行 (SM-Banks) | 城商行/农商行 |
| 880474 | 多元金融 (Multi-Finance) | 非银金融 |
| 880538 | 参股金融 | — |
| 880592 | 互联金融 | — |
| 880705 | 氢能源 | — |
| 880951 | 新能源车 | — |
| 880972 | 雅江水电概念 | — |
| 880981 | TDX 能源 | — |
| 880990 | TDX 金融 | — |

Other major indices stored in the same directory:

| Code | Index |
|------|-------|
| 000001 | 上证指数 (Shanghai Composite) |
| 000300 | 沪深300 (CSI 300) |
| 399001 | 深证成指 (SZSE Component) |
| 399006 | 创业板指 (ChiNext) |

### Data File Location

```
vipdoc/sh/lday/sh880305.day    # 电力行业指数日线
vipdoc/sh/lday/sh880471.day    # 银行行业指数日线
vipdoc/sh/lday/sh000300.day    # 沪深300指数日线
```

Industry index files use the same 32-byte binary format as individual stock `.day` files — parse with the same `struct.unpack('<iiiiifii', ...)` method. No exchange prefix confusion since all 880xxx are in `sh/`.

### Multi-level Index Types

The col 2 value in `tdxzs.cfg` distinguishes:
- `1` = Major index (like 上证, 沪深300)
- `2` = Industry sector (行业板块 — 电力, 银行, etc.)
- `3` = Region (地区板块)
- `4` = Concept (概念板块)
- `5` = Style (风格板块)
