#!/usr/bin/env python3
"""日线形态速检：区间位置 / 影线明细 / 量能比 / 均线位置

用法:
    python3 kline_shadow_check.py 002039          # 默认 150 条
    python3 kline_shadow_check.py 002039 320

数据源: 腾讯 ifzq（前复权）。取不到时改用新浪 K-line（不复权，见 SKILL.md 的 API 表）。
"""
import sys
import json
import urllib.request

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def fetch(code: str, n: int = 150):
    if code[0] in "03":
        prefix = "sz"
    elif code[0] in "69":
        prefix = "sh"
    else:
        prefix = "bj"
    sym = prefix + code
    url = (
        "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        f"?param={sym},day,,,{n},qfq"
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    payload = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
    node = payload.get("data", {}).get(sym, {})
    rows = node.get("qfqday") or node.get("day")
    if not rows:
        raise SystemExit(f"未取到 {sym} 的日线；检查代码，或改用新浪 K-line")
    # 字段顺序: date, open, close, high, low, volume —— close 在 high/low 之前！
    return [
        dict(
            date=r[0],
            o=float(r[1]),
            c=float(r[2]),
            h=float(r[3]),
            l=float(r[4]),
            v=float(r[5]),
        )
        for r in rows
    ]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    code = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    bars = fetch(code, n)
    last = bars[-1]

    hi = max(b["h"] for b in bars)
    lo = min(b["l"] for b in bars)
    pos = (last["c"] - lo) / (hi - lo) * 100 if hi > lo else 0.0
    print(f"{code}  样本 {len(bars)} 条  {bars[0]['date']} ~ {last['date']}")
    print(f"区间 {lo:.2f} ~ {hi:.2f}   现价 {last['c']:.2f}   → 位置 {pos:.1f}% 分位")
    if pos >= 80:
        print("  → 高位区（>80%），形态才具备“高位”前提")
    elif pos >= 60:
        print("  → 中高位区，注意区分“阶段高位”与“历史高位”")
    else:
        print("  → 区间中位及以下，谈不上“历史高位”")
    print()

    print("最近 12 日：")
    print("日期        开     高     低     收    涨跌%   上影   下影   实体  影线/振幅  量(手)")
    start = max(1, len(bars) - 12)
    for i in range(start, len(bars)):
        b = bars[i]
        chg = (b["c"] / bars[i - 1]["c"] - 1) * 100
        upper = b["h"] - max(b["o"], b["c"])
        lower = min(b["o"], b["c"]) - b["l"]
        body = abs(b["c"] - b["o"])
        rng = b["h"] - b["l"]
        shadow_pct = (upper + lower) / rng * 100 if rng else 0.0
        print(
            f"{b['date']} {b['o']:6.2f} {b['h']:6.2f} {b['l']:6.2f} {b['c']:6.2f} "
            f"{chg:+6.2f}% {upper:5.2f} {lower:5.2f} {body:5.2f}  "
            f"{shadow_pct:6.0f}%  {b['v']:>9,.0f}"
        )

    vols = [b["v"] for b in bars]
    ma5v = sum(vols[-5:]) / 5
    ma20v = sum(vols[-20:]) / 20
    ratio = ma5v / ma20v if ma20v else 0.0
    if ratio < 1.2:
        tag = "缩量 → 换手/洗盘"
    elif ratio < 1.5:
        tag = "温和放量"
    else:
        tag = "显著放量 → 若价格不涨即为放量滞涨（出货特征）"
    print()
    print(f"量能：5日均 {ma5v:,.0f} 手 / 20日均 {ma20v:,.0f} 手 = {ratio:.2f}   {tag}")

    print()
    for period in (5, 10, 20, 60):
        if len(bars) >= period:
            ma = sum(b["c"] for b in bars[-period:]) / period
            side = "上方" if last["c"] > ma else "下方"
            print(f"  MA{period:<2} = {ma:6.2f}   现价在其{side}")

    print()
    print(
        "研判提示：影线占振幅 ≥60% 且实体极小 = 多空拉锯；"
        "但必须结合**绝对幅度**（<1.5% 属温和）和**量能**——缩量+长影线 ≠ 出货。"
    )


if __name__ == "__main__":
    main()
