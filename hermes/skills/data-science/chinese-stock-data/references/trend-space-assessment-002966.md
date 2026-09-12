# Worked Example: 苏州银行 002966 趋势与空间研判 (2026-09-01)

User asked "研判下一步可能的趋势和空间" after a +31% rally from the June low. This is the full data set and reasoning that produced the delivered scenario analysis — use as calibration for future assessments.

## Data gathered (all online, RDP drive unmounted)

- K-line: push2his `lmt=320` → 2025-05-14 ~ 2026-09-01, 320 bars. fields2 f51-f61 (incl. pct change per bar).
- Real-time: Tencent qt.gtimg.cn — close 9.06 (+1.91%), vol 47.6万手.
- Fundamentals: push2 stock/get → PB×100=76, total mkt cap 405亿. PE cross-checked via 市值/净利润 (Tencent field 38 returned wrong value).

## Key computed values

| Item | Value |
|------|-------|
| Prior high (last 15mo) | **9.12 @ 2025-07-04** — current price 9.06 = 0.7% below, at 97th percentile of range 6.92~9.12 |
| Prior test behavior | July 2025: touched 9.12 → sideways 1 week → -15% over 6 weeks to 7.76 (volume-less top, no catalyst) — the warning template |
| Fib from low 6.92 | 0.382=7.76, 0.5=8.02, 0.618=8.28, 1.0=9.12, **1.272=9.72**, **1.618=10.48** |
| Virgin territory | 0 historical closes ≥9.5 or ≥10.0 (only 3 days ≥9.0) — friction expected above 9.5 |
| Monthly avg volume (万手) | Feb 28 → Mar 34 → Apr 27 → May 28 → Jun 46 → Jul 54 → Aug 36 → Sep 48 (rising into breakout = quality) |
| Max drawdown since 6/29 low | -7.5% (shallow pullbacks = strong structure) |
| PB mapping | 9.06→0.76x, 9.72→~0.81x, 10.48→~0.88x — even the optimistic target stays below peer-average ~0.9x; constraint is technical (trapped supply at prior high), not valuation |

## Delivered scenarios (user accepted format)

| Scenario | Prob | Path | Target |
|----------|:---:|------|--------|
| Base: consolidate then break | 50% | 8.9~9.12 digest 1-3 weeks, hold above 9.12 | 9.5~9.7 (+4~7%) |
| Bullish: direct volume breakout | 25% | >50万手 close above 9.12 + sector β (Q3 NIM data, LPR cut, year-end dividend flows) | 10~10.5 (+10~16%) |
| Bearish: repeat failed test | 25% | volume-less upper shadow at 9.1-9.15, profit-taking after +31% | retest 8.3~8.6 (-5~-8%) |

Confirmation signals given to user:
1. Breakout confirmed = close >9.12 on >50万手 volume → targets activate.
2. Failure warning = upper shadow at 9.1-9.15 without next-day recovery → treat as bearish; MA20 (8.55) break = trend damage.

## What made the answer land well

- Anchored everything to the concrete prior-high level with a historical precedent (last test failed — and WHY it failed, vs why this attempt differs: earnings catalyst + volume).
- Scenario table with explicit probabilities + confirmation/invalidation signals, not vague "还有空间".
- Valuation cross-check showed even the bull case is cheap → framed the constraint as technical supply, which is actionable (watch volume at 9.12).
