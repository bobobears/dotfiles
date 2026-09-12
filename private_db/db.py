#!/usr/bin/env python3
"""私人数据库查询助手

用法:
  python3 db.py watchlist        查看自选股
  python3 db.py scores           查看最近评分
  python3 db.py trades           查看交易记录
  python3 db.py notes <代码>     查看个股笔记
  python3 db.py sql "SELECT ..." 执行任意SQL
  python3 db.py backup           备份数据库
"""
import sqlite3, os, shutil, sys
from datetime import date

DB_PATH = os.path.expanduser("~/private_db/private.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def print_table(rows, title=None):
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print('='*60)
    if not rows:
        print("  (空)")
        return
    keys = rows[0].keys()
    col_widths = {k: max(len(k), max(len(str(r[k] or "")) for r in rows)) + 2 for k in keys}
    header = "  " + "".join(k.ljust(col_widths[k]) for k in keys)
    sep    = "  " + "".join("-" * col_widths[k] for k in keys)
    print(header)
    print(sep)
    for r in rows:
        line = "  " + "".join(str(r[k] or "").ljust(col_widths[k]) for k in keys)
        print(line)
    print(f"  ({len(rows)} 行)")

def cmd_watchlist():
    conn = get_conn()
    rows = conn.execute("""
        SELECT code, name, sector, priority, added_date, notes
        FROM watchlist WHERE active=1
        ORDER BY priority DESC, code
    """).fetchall()
    print_table(rows, "自选股列表")
    conn.close()

def cmd_scores():
    conn = get_conn()
    rows = conn.execute("""
        SELECT w.code, w.name, d.date, d.score, d.trend, d.action
        FROM daily_scores d
        JOIN watchlist w ON w.code = d.code
        WHERE d.date = (SELECT MAX(date) FROM daily_scores)
        ORDER BY d.score DESC
    """).fetchall()
    print_table(rows, "最新评分")
    conn.close()

def cmd_trades():
    conn = get_conn()
    rows = conn.execute("""
        SELECT w.name, t.code, t.trade_date, t.direction, t.price, t.shares,
               printf('%.2f', t.price * t.shares) AS amount, t.notes
        FROM trades t
        JOIN watchlist w ON w.code = t.code
        ORDER BY t.trade_date DESC
        LIMIT 20
    """).fetchall()
    print_table(rows, "交易记录（最近20条）")
    conn.close()

def cmd_notes(code):
    conn = get_conn()
    rows = conn.execute("""
        SELECT id, title, content, created_at
        FROM stock_notes WHERE code = ?
        ORDER BY created_at DESC
    """, (code,)).fetchall()
    print_table(rows, f"个股笔记 - {code}")
    conn.close()

def cmd_sql(query):
    conn = get_conn()
    try:
        cur = conn.execute(query)
        if query.strip().upper().startswith(("SELECT", "PRAGMA")):
            rows = cur.fetchall()
            print_table(rows, "SQL 查询结果")
        else:
            conn.commit()
            print(f"✅ 影响行数: {cur.rowcount}")
    except Exception as e:
        print(f"❌ SQL 错误: {e}")
    conn.close()

def cmd_backup():
    backup_path = os.path.expanduser(f"~/private_db/backups/private_{date.today().isoformat()}.db")
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    shutil.copy2(DB_PATH, backup_path)
    print(f"✅ 已备份到: {backup_path}")

def help_text():
    print("""
用法: python3 db.py <命令> [参数]

命令:
  watchlist              查看自选股
  scores                 查看最新评分（来自 DSA）
  trades                 查看最近交易记录
  notes    <代码>        查看个股笔记
  sql      "SELECT ..."  执行任意 SQL
  backup                 备份数据库到 backups/
""")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        help_text()
        sys.exit(1)

    cmd = sys.argv[1]
    cmds = {
        "watchlist": cmd_watchlist,
        "scores":    cmd_scores,
        "trades":    cmd_trades,
        "backup":    cmd_backup,
    }
    if cmd in cmds:
        cmds[cmd]()
    elif cmd == "notes" and len(sys.argv) >= 3:
        cmd_notes(sys.argv[2])
    elif cmd == "sql" and len(sys.argv) >= 3:
        cmd_sql(" ".join(sys.argv[2:]))
    else:
        help_text()
