# 个股异动/利空核查工作流（"为什么XX低开/大跌？有没有特殊信息？"）

Verified 2026-08-14（黔源电力 002039 盘中最低 19.00 核查）——全部端点从中国大陆直连可用，无需 auth。

适用场景：用户问某只自选股今天低开/异动/大跌，怀疑有公告、传闻或特殊信息。核查顺序即下面编号。

## 0. 先拿实时盘面——区分"低开"还是"盘中下探"

用户说"开盘低开 19.00 左右"，实际往往是指**盘中最低价**（黔源电力开盘 19.29 仅微跌 0.1%，最低 19.00 是开盘后下探）。先核对再下结论。

Tencent qt.gtimg.cn 88 字段（`~` 分割，0-based）：
- 3=现价, 4=昨收, 5=今开, 33=最高, 34=最低, 32=涨跌幅%, 38=换手率

```bash
curl -s "https://qt.gtimg.cn/q=sz002039" | iconv -f GBK -t UTF-8
```

分时（分钟级价格轨迹，判断开盘瞬间 vs 盘中持续走弱）：
```bash
curl -s "https://web.ifzq.gtimg.cn/appstock/app/minute/query?code=sz002039"
# data.data.sz002039.data.data = rows [HHMM, price, volume, amount]，每天约240行
```

## 1. 正式公告（东财公告 API）—— 排除公司层面利空

```bash
curl -sL -A "Mozilla/5.0" "https://np-anotice-stock.eastmoney.com/api/security/ann?sr=-1&page_size=50&page_index=1&ann_type=A&client_source=web&stock_list=002039"
# stock_list = 6位纯数字，无 sz/sh 前缀
# 看 notice_date 是否 >= 今天/本周；columns[].column_name 为公告分类
# "8月以来零新公告" = 无公司层面突发利空
```

## 2. 新闻搜索（东财 search-api-web，JSONP）—— 查报道/传闻

技能 SKILL.md 的 API 可用性表曾标注此端点 404，**已过时**——`search-api-web.eastmoney.com` 工作正常。

```bash
# keyword 为 URL 编码的中文，type 固定 ["cmsArticleWebOld"]
curl -sL -A "Mozilla/5.0" "https://search-api-web.eastmoney.com/search/jsonp?cb=jQuery&param=%7B%22uid%22%3A%22%22%2C%22keyword%22%3A%22%E9%BB%94%E6%BA%90%E7%94%B5%E5%8A%9B%22%2C%22type%22%3A%5B%22cmsArticleWebOld%22%5D%2C%22client%22%3A%22web%22%2C%22clientType%22%3A%22web%22%2C%22clientVersion%22%3A%22curr%22%2C%22param%22%3A%7B%22cmsArticleWebOld%22%3A%7B%22searchScope%22%3A%22default%22%2C%22sort%22%3A%22default%22%2C%22pageIndex%22%3A1%2C%22pageSize%22%3A10%2C%22preTag%22%3A%22%3Cem%3E%22%2C%22postTag%22%3A%22%3C%2Fem%3E%22%7D%7D%7D"
```

- 返回 JSONP（`jQuery({...})`），用 `re.search(r'jQuery\((.*)\)\s*$', c, re.DOTALL)` + `json.loads` 剥壳
- `hitsTotal` 为总命中数；`result.cmsArticleWebOld[]` 每项含 `date/title/content/mediaName/url`
- 关键词建议：股票名、股票名+异动、股票名+大跌、股票名+公告、股票名+中报。`title` 里的 `<em>` 标签用 `re.sub(r'</?em>','',...)` 清理
- 若命中是当天/昨天的个股新闻，逐条读；若无个股命中，说明无媒体报道

## 3. 龙虎榜 / 大宗交易 / 融资融券（datacenter-web，需 DNS 绕过）

路由器 DNS 屏蔽 datacenter-web，用 114 DNS 解析后 `--resolve`：

```bash
IP=$(host datacenter-web.eastmoney.com 114.114.114.114 | grep -oP 'has address \K[0-9.]+')
curl -sL -A "Mozilla/5.0" "https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_DAILYBILLBOARD_DETAILSNEW&columns=ALL&filter=(SECURITY_CODE%3D%22002039%22)&sortColumns=TRADE_DATE&sortTypes=-1&pageSize=10" --resolve "datacenter-web.eastmoney.com:443:${IP}"
```

| 数据 | reportName | filter 字段 |
|------|-----------|-----------|
| 龙虎榜 | RPT_DAILYBILLBOARD_DETAILSNEW | SECURITY_CODE |
| 大宗交易 | RPT_DATA_BLOCKTRADE | SECURITY_CODE |
| 融资融券 | RPT_MARGIN_DAILY | **scode**（注意不是 SECURITY_CODE） |

注意：报表名不对会返回 `{"message":"报表配置不存在","code":9501}`，换 reportName 再试。

## 4. 股吧情绪（eastmoney guba）—— 查流传中的消息

```bash
curl -sL -A "Mozilla/5.0" "https://guba.eastmoney.com/list,002039.html"
# 提取 <a class="note" title="..."> 的 title 属性 = 帖子标题
# 页面自带日期（MM-DD），过滤出今天的帖子；提及"财报/增发电/减持/重组"等关键词的帖子重点看
```

股吧是散户情绪场，只作线索（如"下周出财报"、"周末起雨期"），不作结论依据。

## 5. K线背景 —— 判断"单日事件" vs "多日趋势"

```bash
curl -sL "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=0.002039&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57&klt=101&fqt=1&end=20260814&lmt=15"
# klines = [date, open, close, high, low, volume, amount] 字符串，逗号分隔
# secid 前缀：沪=1. 深=0. 创业板=3.
```

看 10-15 日走势：若连续多日缩量回调 + 无新公告 → 技术调整/财报观望，非利空事件。成交量对比（当日 vs 前几日）很重要：**缩量阴跌=抛压不大**。

## 6. 财报披露日 —— 最常被忽略的"走弱原因"

业绩预告已兑现利好、正式财报披露前 1-2 周常出现"利好出尽/观望"回调。用同花顺 F10 查预约披露日：

```bash
curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" "https://basic.10jqka.com.cn/002039/"
# 页面文本含 "预约<YYYY-MM-DD>披露2026年中报"（GBK 编码，必要时 iconv）
# 直接在 HTML 里 re.findall(r'20\d\d-\d\d-\d\d') 也能抓到关键日期
```

## 7. 大盘对照 —— 个股独立 vs 跟随大盘

```bash
curl -s "https://qt.gtimg.cn/q=sh000001" | iconv -f GBK -t UTF-8
# 上证指数 index 32 = 涨跌幅。个股跌而大盘涨 = 个股独立走弱，需找个股原因；
# 大盘同跌 = 跟随系统性回调，个股原因权重降低
```

## 结论模板（给用户）

- 官方渠道（公告/龙虎榜/大宗/新闻）均无利空 → 明确告知"**没有特殊信息**"，列出已核查项
- 有披露日临近 → 指出最可能的走弱原因（财报观望/利好兑现）
- 缩量 + 多日回调 → 技术调整而非恐慌，给出操作参考（如关注披露日）
