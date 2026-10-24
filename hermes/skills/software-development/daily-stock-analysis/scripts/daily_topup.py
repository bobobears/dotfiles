#!/usr/bin/env python3
"""DSA 每日盘后数据补齐（cron watchdog 模式）

流程：交易日检查 → 股票(main.py) → ETF(fetch_etf_daily.py) → 12 标的完整性校验
输出：全齐 → 无输出（no_agent 下即不推送）；有缺失/失败 → 打印告警

配合 cron: schedule='30 16 * * 1-5', no_agent=true, script=<~/.hermes/scripts/ 下的包装脚本>
"""
import subprocess, sqlite3, sys
from datetime import datetime

DSA = '/home/bobobears/dsa'
PY = f'{DSA}/venv/bin/python'
DB = f'{DSA}/data/stock_analysis.db'
CODES = ['002039', '002047', '002966', '300706', '300750',
         '301228', '301306', '301392', '688603', '159819', '515080', '510500']

problems = []

# 1) 交易日判断（非交易日静默退出）
try:
    r = subprocess.run([sys.executable, '/home/bobobears/private_db/is_trading_day.py'],
                       capture_output=True, text=True, timeout=60)
    out = (r.stdout or '') + (r.stderr or '')
    if not any(k in out for k in ['是', 'true', 'True', '交易日']):
        sys.exit(0)
except Exception as e:
    problems.append(f'交易日检查异常: {e}')

# 2) 股票数据（--dry-run 只取数不跑 LLM）
try:
    r = subprocess.run([PY, 'main.py', '--dry-run', '--no-market-review'],
                       cwd=DSA, capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        problems.append(f'main.py 退出码 {r.returncode}: '
                        f'{(r.stderr or r.stdout or "")[-400:]}')
except Exception as e:
    problems.append(f'main.py 执行异常: {e}')

# 3) ETF 数据
try:
    r = subprocess.run([PY, 'fetch_etf_daily.py'], cwd=DSA,
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        problems.append(f'ETF脚本失败: {(r.stderr or "")[-300:]}')
except Exception as e:
    problems.append(f'ETF 执行异常: {e}')

# 4) 完整性校验：12 个标的当日全覆盖
today = datetime.now().strftime('%Y-%m-%d')
try:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    missing = []
    for c in CODES:
        cur.execute('SELECT 1 FROM stock_daily WHERE code=? AND date=?', (c, today))
        if not cur.fetchone():
            missing.append(c)
    if missing:
        detail = []
        for c in missing:
            cur.execute('SELECT MAX(date) FROM stock_daily WHERE code=?', (c,))
            detail.append(f'{c}(最新{cur.fetchone()[0]})')
        problems.append(f'{today} 缺失 {len(missing)} 个标的: ' + '、'.join(detail))
    conn.close()
except Exception as e:
    problems.append(f'校验异常: {e}')

if problems:
    print(f'⚠️ 盘后数据补齐异常（{today}）')
    for p in problems:
        print(f'- {p}')
sys.exit(0)
