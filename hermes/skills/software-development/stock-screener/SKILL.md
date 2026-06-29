---
name: stock-screener
description: "Use when the user asks to screen/filter/search A-share stocks by quantitative criteria: market cap, volume ratio, ROE, price trend, or any combination. Covers data sources (Tencent, Sina, Tushare, 同花顺), step-by-step filtering pipeline, and reusable scripts."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [a-share, stock-screening, finance, chinese-stocks, tushare]
    related_skills: [daily-stock-analysis, plan]
---

# A股量化选股筛选器

## Overview

筛选 A 股是用户在投资场景中的高频需求。本技能封装了从**获取全量股票 → 提取行情 → 叠加财务/技术指标 → 输出推荐**的完整流水线，基于四大数据源组合工作：

| 数据源 | 用途 | 特点 |
|--------|------|------|
| **新浪财经** `vip.stock.finance.sina.com.cn` | 获取全A股代码列表 | 快，无需认证，一次获取~5000只 |
| **腾讯行情** `qt.gtimg.cn` | 实时行情（价/量/市值/量比） | 快，批量查询，100只/请求 |
| **Tushare Pro** | 历史日K线（趋势/均线判断） | 免费版限速（1次/分钟，200次/天） |
| **同花顺** (akshare) `stock_financial_abstract_ths` | 财务指标（ROE/净利率等） | 无认证，逐只查询 |

## When to Use

- 用户要求推荐/筛选/搜索 A 股
- 条件包含：流通市值、换手率、量比、ROE、PE、趋势（均线/涨跌幅）
- 用户要求按财务指标 + 技术形态综合选股
- 用户说"帮我看看XX条件有哪些股票"

**不适合使用：**
- 单只股票详细分析（用 `daily-stock-analysis`）
- 需要实时成交明细/Level2数据（数据源不支持）

## Data Source Details

### 1️⃣ 新浪 — 获取全量股票代码

```python
import urllib.request, json, re

def get_all_stock_codes():
    """获取沪深全部A股代码"""
    codes, names = [], {}
    for node in ['sh_a', 'sz_a']:
        page = 1
        while True:
            url = f"https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeDataSimple?page={page}&num=10000&sort=symbol&asc=1&node={node}&symbol=&_s_r_a=page"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.sina.com.cn/'})
            data = urllib.request.urlopen(req, timeout=15).read().decode('gbk')
            if not data or data == 'null': break
            stocks = json.loads(re.sub(r'/\*.*?\*/', '', data, flags=re.DOTALL))
            if not stocks: break
            for s in stocks:
                c = s.get('code', '')
                n = s.get('name', '')
                if c and not c.startswith('8'):
                    codes.append(c)
                    names[c] = n
            if len(stocks) < 10000: break
            page += 1
    return codes, names
```

- 返回格式：`[{"code":"600519","name":"贵州茅台"}, ...]`
- 使用 `gbk` 编码解码，可能有 JS 注释需 regex 清理
- 过滤北交所代码（`8` 开头）和 ST 股

### 2️⃣ 腾讯行情 — 批量实时行情

```python
def get_tencent_batch(codes):
    """批量获取实时行情（100只/批）"""
    results = []
    for i in range(0, len(codes), 100):
        batch = codes[i:i+100]
        qs = ','.join([f"sh{c}" if c.startswith('6') else f"sz{c}" for c in batch])
        req = urllib.request.Request(f"https://qt.gtimg.cn/q={qs}",
            headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.qq.com/'})
        text = urllib.request.urlopen(req, timeout=30).read().decode('gbk')
        for line in text.strip().split(';'):
            parts = line.split('="')[1].rstrip('";').split('~')
            if len(parts) < 50: continue
            results.append({
                'code': parts[2],
                'name': parts[1],
                'price': float(parts[3]) if parts[3] else 0,
                'pct': float(parts[38]) if len(parts)>38 and parts[38] else 0,      # 涨跌幅%
                'circ_mv': float(parts[44]) if len(parts)>44 and parts[44] else 0,   # 流通市值(亿)
                'vol_ratio': float(parts[46]) if len(parts)>46 and parts[46] else 0, # 量比
            })
        time.sleep(0.2)
    return results
```

**关键字段索引（腾讯API `~` 分隔）：**
| 索引 | 字段 | 单位 |
|------|------|------|
| 3 | 现价 | 元 |
| 4 | 昨收 | 元 |
| 5 | 今开 | 元 |
| 38 | 涨跌幅 | % |
| 44 | 流通市值 | 亿 |
| 46 | 量比 | — |
| 29 | 时间戳 | yyyyMMddHHmmss |

### 3️⃣ Tushare — 历史K线（趋势/均线）

```python
import tushare as ts
pro = ts.pro_api('your_token')

def get_kline(code):
    """获取日K线，用于均线/趋势分析"""
    ts_code = code + (".SH" if code.startswith('6') else ".SZ")
    df = pro.daily(ts_code=ts_code, start_date='20260501', end_date='20260626')
    df = df.sort_values('trade_date').reset_index(drop=True)
    return df
```

**趋势判断指标：**
- 价 > MA5 (+25分)
- 价 > MA20 (+25分)
- MA5 > MA10 > MA20（多头排列，+30分）
- MA10 方向向上 (+10分)
- 5日上涨 (+10分)
- 总分 ≥ 55 → "上升趋势"，≥ 80 → "强势上升"

**限速说明：** 免费版 Tushare 200次/天，每次调用需间隔 1 秒以上

### 4️⃣ 同花顺 — ROE 财务指标

```python
import akshare as ak
df = ak.stock_financial_abstract_ths(symbol='600519')
roe = df['净资产收益率'].iloc[0]  # 最新一期ROE
```

返回包含 25+ 财务指标：净利润、营收、每股收益、净利率、毛利率、**净资产收益率（ROE）**、资产负债率等。

## Filtering Pipeline

```
全量股票(~5000只)
  │
  ├─ Step 1: 新浪获取代码列表
  │
  ├─ Step 2: 腾讯批量行情 → circ_mv, vol_ratio, pct
  │
  ├─ Step 3: 粗筛 (市值+量比+涨跌幅)
  │
  ├─ Step 4: 同花顺获取 ROE
  │         (只查粗筛后的前30-50只，避免超时)
  │
  ├─ Step 5: Tushare日K线 → 均线趋势分析
  │         (只查ROE≥阈值的股票)
  │
  └─ Step 6: 输出最终推荐
```

### 常用筛选阈值

```python
# 用户配置的筛选条件
conditions = {
    'circ_mv_min': 50,       # 流通市值下限(亿)
    'circ_mv_max': 100,      # 流通市值上限(亿)
    'vol_ratio_min': 1.5,    # 量比下限
    'roe_min': 10.0,         # ROE下限(%)
    'pct_today_min': 0,      # 今日涨幅下限(0=上涨)
    'exclude_st': True,      # 排除ST股
}
```

## Common Pitfalls

1. **腾讯行情API没有ROE：** 必须用同花顺或Tushare另查财务数据，不能指望行情API给出ROE
2. **Tushare限速：** 免费版 `daily` API 有频率限制（约1次/秒）。对前30只候选股逐一查K线，每次延迟1秒以上
3. **同花顺耗时：** `stock_financial_abstract_ths` 每次约 0.3-0.5 秒，50只要15-25秒。建议只查前30只候选股
4. **新浪加解密：** 返回 `gbk` 编码，需解码。偶尔返回带 JS 注释的数据，需用 `re.sub(r'/\\*.*?\\*/', '', data)` 清理
5. **腾讯 stock 代码前缀：** `6` 开头 → `sh`，`0`/`3` 开头 → `sz`，`8`/`4` 开头 → `bj`（北交所）
6. **千股批量：** 腾讯API单次可查100只，~5000只需52次请求，总耗时约15秒
7. **ST过滤：** ST股量比可能异常高(几百)，必须在筛选前过滤掉
8. **测试日无数据：** 周末/节假日Tushare日线无数据。用 `is_trade_date=pro.trade_cal(start_date=...)` 检查
9. **Tushare `daily_basic` 无量比：** 免费版 Tushare 调用 `daily_basic(volume_ratio=True)` 返回的 `volume_ratio` 字段全部为 `None`。量比数据不能从 Tushare 获取，必须用腾讯API（`qt.gtimg.cn` 字段[46]）作为来源
10. **腾讯K线API不可靠：** `web.ifzq.gtimg.cn/appstock/app/kline/mkline` 和 `fqkline/get` 接口返回 `"bad params"` 或 `"param error"`，无法获取历史日K线。备用方案：① 搜狐 `q.stock.sohu.com/hisHq`（偶尔可用）；② Tushare `pro.daily()`（最可靠，但需注意限速）；③ 通达信 `.day` 文件解析（离线最快）
11. **搜狐K线不稳定：** `q.stock.sohu.com/hisHq` 也经常断开或返回空数据。趋势分析建议优先走 Tushare `daily` API，搜狐仅作备用

## Verification Checklist

- [ ] 获取了正确的股票数量（沪深A股约5000只）
- [ ] 流通市值字段单位确认是"亿"（腾讯API返回就是亿）
- [ ] ROE单位确认是百分比（同花顺返回带 % 符号需 strip）
- [ ] 趋势评分逻辑检查无误（分值权重合理）
- [ ] 排除了北交所(8开头)和ST股
- [ ] 量比>1.5 不是异常值（排除日线第一次交易的股）
- [ ] 所有API调用有足够的 time.sleep 防限速
- [ ] 输出格式清晰，每只股附带推荐理由

## One-Shot Recipe: 完整选股脚本

将 `/tmp/screener_ultimate.py` 内容作为完整参考脚本。核心调用流程：

```bash
cd /path/to/project && source venv/bin/activate && python3 /tmp/screener_ultimate.py
```

如需修改筛选条件，编辑脚本头部的 `conditions` 字典即可。

> 📖 所有API的返回格式、字段索引、响应示例详见 `references/data-sources.md`
