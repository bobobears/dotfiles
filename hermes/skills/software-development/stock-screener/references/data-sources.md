# A股数据源API参考

## 腾讯行情 API (qt.gtimg.cn) — ✅ 可用

```bash
# 批量查询，最多约200只/次
curl 'https://qt.gtimg.cn/q=sh600519,sz002039,sz301392' -H 'User-Agent: Mozilla/5.0'
```

### 返回格式

每行一条，`~` 分隔，`v_{code}="51~name~code~..."`

| 索引 | 字段 | 单位 | 示例(002039) |
|------|------|------|-------------|
| 3 | 现价 | 元 | 18.78 |
| 4 | 昨收 | 元 | 19.03 |
| 5 | 今开 | 元 | 19.16 |
| 6 | 成交量 | 手 | 72161 |
| 29 | 时间戳 | yyyyMMddHHmmss | 20260626161421 |
| 30 | 涨跌额 | 元 | -0.25 |
| 31 | 涨跌幅 | % | -1.31 |
| 32 | 最高 | 元 | 19.31 |
| 33 | 最低 | 元 | 18.70 |
| 38 | 换手率 | % | 1.69 |
| 39 | 市盈率 | — | 12.60 |
| 44 | **流通市值** | **亿** | **80.30** ← 筛选核心字段 |
| 45 | 总市值 | 亿 | 80.30 |
| 46 | **量比** | — | **1.84** ← 筛选核心字段 |

- 编码：gbk
- 分隔：`v_code="..."` — 按 `="` 分割取右侧去 `";`，再按 `~` split
- 空字段为 `""`（两个`~~`相邻）
- 响应包含较多无用字段（买卖盘口等），但解析只需关注上述索引

### 代码前缀规则

- `6` 开头 → `sh`（上交所主板/科创板）
- `0` 开头 → `sz`（深交所主板）
- `3` 开头 → `sz`（深交所创业板，含 300/301）
- `68` 开头 → `sh`（科创板）
- `8`/`4` 开头 → `bj`（北交所，筛选时建议排除）

---

## 新浪股票列表 API (vip.stock.finance.sina.com.cn) — ✅ 可用

```bash
# 上海A股
curl 'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeDataSimple?page=1&num=10000&sort=symbol&asc=1&node=sh_a'
   -H 'User-Agent: Mozilla/5.0' -H 'Referer: https://finance.sina.com.cn/'
```

### 返回格式

```json
[{"code":"600000","name":"浦发银行"},{"code":"600004","name":"白云机场"},...]
```

- 编码：gbk
- 节点：`sh_a`（上海主板+科创）、`sz_a`（深圳主板+创业板）
- 一次最多返回10000只，通常一页就能拿完所有
- 需要清理可能的 JS 注释：`re.sub(r'/\*.*?\*/', '', data)`

### 筛选字段

只返回 `code` 和 `name`，**没有行情数据**。仅用于获取全量代码列表。

---

## 同花顺财务数据 (akshare) — ✅ 可用

```python
import akshare as ak
df = ak.stock_financial_abstract_ths(symbol='301392')
```

### 返回字段示例

| 指标 | 值 |
|------|-----|
| 净资产收益率 (ROE) | 23.65% |
| 每股净资产 | 12.34 |
| 净利润 | 1.23亿 |
| 营业收入 | 5.67亿 |
| 每股收益 | 0.89 |
| 净利率 | 18.5% |
| 毛利率 | 35.2% |

- 速度：~0.3-0.5秒/只
- 无认证要求
- 返回最新的财务报告数据（季报/中报/年报）
- ROE 值带 `%` 符号，需 `float(val.replace('%',''))`

---

## Tushare API — ✅ 可用但有限速

```python
import tushare as ts
pro = ts.pro_api('your_token')
```

### 可用接口

| 接口 | 用途 | 免费版限制 |
|------|------|-----------|
| `pro.daily()` | 历史日K线（趋势/均线） | 200次/天，约1次/秒 |
| `pro.daily_basic(trade_date=..., fields='volume_ratio,circ_mv')` | 基础行情指标 | **⚠️ volume_ratio 返回值为 None（免费版不可用）** |

### 趋势分析代码

```python
def check_trend_tushare(code):
    import tushare as ts
    pro = ts.pro_api()
    ts_code = code + (".SH" if code.startswith('6') else ".SZ")
    df = pro.daily(ts_code=ts_code, start_date='20260501', end_date='20260626')
    if df is None or len(df) < 20:
        return False, 0, "数据不足"
    df = df.sort_values('trade_date')
    closes = df['close'].values

    ma5 = closes[-5:].mean()
    ma10 = closes[-10:].mean()
    ma20 = closes[-20:].mean()
    cur = closes[-1]

    score = 0
    reasons = []
    if cur > ma5: score += 25; reasons.append(f"价>MA5({ma5:.2f})")
    if cur > ma20: score += 25; reasons.append(f"价>MA20({ma20:.2f})")
    if ma5 > ma10 > ma20: score += 30; reasons.append("多头排列")
    if len(closes) >= 5:
        chg5 = (cur/closes[-5]-1)*100
        if chg5 > 0: score += 10; reasons.append(f"5日涨{chg5:.1f}%")

    return score >= 55, score, ' | '.join(reasons)
```

**评分规则：** ≥55 = 上升趋势，≥80 = 强势上升，<55 = 震荡/下跌

---

## ❌ 不可用/不可靠的K线API

| API | 尝试结果 |
|-----|---------|
| `web.ifzq.gtimg.cn/appstock/app/kline/mkline` | 返回 `"bad params"`，无法修复 |
| `web.ifzq.gtimg.cn/appstock/app/fqkline/get` | 返回 `"param error"`，无法修复 |
| `q.stock.sohu.com/hisHq` | 偶尔返回数据但极不稳定，经常空响应 |
| `push2.eastmoney.com` | HTTP 000/302，DNS/网络阻断 |
| `nufm.dfcfw.com` | 302 重定向，无法正常获取 |
