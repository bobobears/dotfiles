# 东方财富公告 API — 业绩预告 / 公告 / 定期报告查询

Verified working 2026-07-30 from mainland China (DGX Spark), no auth required.
Used to retrieve 黔源电力 (002039) 2026年半年度业绩预告.

## Pipeline (3 HTTP calls + pdftotext)

### 1. Search announcements for a stock

```
GET https://np-anotice-stock.eastmoney.com/api/security/ann
    ?sr=-1&page_size=50&page_index=1&ann_type=A&client_source=web&stock_list=002039
```

- `stock_list` = plain 6-digit code (NO `sz`/`sh` prefix, NO dot suffix)
- `page_size` up to 50; `ann_type=A` = all announcements
- Returns JSON: `data.list[]` with fields:
  - `art_code` (e.g. `AN202607091826845120`) — the key for step 2
  - `title` (e.g. `黔源电力:2026年半年度业绩预告`)
  - `notice_date` (e.g. `2026-07-10 00:00:00`)
  - `columns[].column_name` (公告分类, e.g. 分配预案)
  - `codes[].short_name`

Timing: 业绩预告 typically published 1–2 weeks after period end
(e.g. H1 业绩预告 → early-to-mid July). Recent-50 list usually covers it.

### 2. Get detail / PDF attachment URL

```
GET https://np-cnotice-stock.eastmoney.com/api/content/ann
    ?art_code=AN202607091826845120&client_source=web&page_index=1
```

Returns JSON: `data.attach_list[]` with
`attach_url` = `https://pdf.dfcfw.com/pdf/H2_AN202607091826845120_1.pdf`

### 3. Download the PDF

```bash
curl -sL -A "Mozilla/5.0" -o /tmp/ann.pdf \
  "https://pdf.dfcfw.com/pdf/H2_AN202607091826845120_1.pdf"
```

The attach_url may carry a cache-buster query (`?1783615597000.pdf`) — stripping it works.

### 4. Extract text

```bash
pdftotext /tmp/ann.pdf /tmp/ann.txt && cat /tmp/ann.txt
```

- `pdftotext` is available at `/usr/bin/pdftotext` (poppler-utils) on this system
- PyMuPDF (`fitz`) and `pdfminer` are NOT installed in system python — use pdftotext
- PDF is 2 pages for a 业绩预告; layout is table-heavy, pdftotext keeps the numbers

## Worked example — 黔源电力 002039 2026 H1 业绩预告

- art_code: `AN202607091826845120`, notice 2026-07-10
- 归母净利润: 22,000 ~ 25,500 万元 (上年同期 12,715.86), 同比 +73.01% ~ +100.54%
- 扣非净利润: 21,800 ~ 25,300 万元, +72.52% ~ +100.22%
- 基本每股收益: 0.5145 ~ 0.5964 元 (上年 0.2974)
- 原因: 来水 +67.40% (北盘江 +22.30%, 三岔河 +56.90%, 芙蓉江 +218.30%);
  发电量 403,618.77 万kWh, 同比 +26.10%
- Bonus context: 2026-07-28 董事长提议制定中期利润分配方案 (分红预期)

## Related: 董事长/股东会 other announcements

Same list endpoint surfaces everything (利润分配预案, 业绩预告, 定期报告, 股东会决议).
For 分红/分配预案 check `columns[].column_name == "分配预案"`.

## DNS note

`np-anotice-stock.eastmoney.com` and `np-cnotice-stock.eastmoney.com` resolved fine
directly this session. If router DNS (192.168.31.1) blocks them later, use the
standard bypass: `host <domain> 114.114.114.114` then
`curl --resolve "<domain>:443:<IP>"` (see SKILL.md DNS Bypass section).
