#!/usr/bin/env python3
"""
从 DSA 每日分析报告中提取评分，写入私人数据库 daily_scores 表。
用法:
  python3 save_dsa_scores.py                       # 自动读取今天的最新报告
  python3 save_dsa_scores.py 20260701               # 读取指定日期报告
  python3 save_dsa_scores.py --file /path/to/report.md
"""
import re
import sqlite3
import os
import sys
from datetime import date, datetime

DB_PATH = os.path.expanduser("~/private_db/private.db")
DSA_REPORT_DIR = os.path.expanduser("~/dsa/reports")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def find_report(date_str=None):
    """查找报告文件路径"""
    if date_str is None:
        date_str = date.today().strftime("%Y%m%d")
    candidates = [
        os.path.join(DSA_REPORT_DIR, f"report_{date_str}.md"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    if not os.path.isdir(DSA_REPORT_DIR):
        return None
    files = sorted(
        [f for f in os.listdir(DSA_REPORT_DIR) if f.startswith("report_") and f.endswith(".md")],
        reverse=True,
    )
    if files:
        return os.path.join(DSA_REPORT_DIR, files[0])
    return None


def parse_report(filepath):
    """从报告中解析股票评分数据。"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    date_match = re.search(r"# 🎯\s*(\d{4}-\d{2}-\d{2})", content)
    report_date = date_match.group(1) if date_match else date.today().isoformat()
    pattern = re.compile(
        r"\*\*(.+?)\((\d{6})\)\*\*:\s*(.+?)\s*\|\s*评分\s*(\d+)\s*\|\s*(.+)"
    )
    stocks = []
    for line in content.split("\n"):
        m = pattern.search(line)
        if m:
            name = m.group(1).strip()
            code = m.group(2).strip()
            action = m.group(3).strip()
            score = int(m.group(4).strip())
            trend = m.group(5).strip()
            stocks.append({"code": code, "name": name, "action": action, "score": score, "trend": trend})
    return report_date, stocks


def write_scores(report_date, stocks):
    """写入 daily_scores 表（INSERT OR IGNORE 防重复）"""
    conn = get_conn()
    inserted = 0
    for s in stocks:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO daily_scores(code, date, score, trend, action)
                VALUES (?, ?, ?, ?, ?)
            """, (s["code"], report_date, s["score"], s["trend"], s["action"]))
            if conn.total_changes > inserted:
                inserted += 1
        except sqlite3.Error as e:
            print(f"  ❌ {s['code']} {s['name']}: {e}", file=sys.stderr)
    conn.commit()
    rows = conn.execute("""
        SELECT w.name, d.code, d.score, d.trend, d.action
        FROM daily_scores d
        JOIN watchlist w ON w.code = d.code
        WHERE d.date = ?
        ORDER BY d.score DESC
    """, (report_date,)).fetchall()
    conn.close()
    return inserted, rows


def main():
    date_str = None
    filepath = None
    for arg in sys.argv[1:]:
        if arg.startswith("--file="):
            filepath = arg.split("=", 1)[1]
        elif arg.startswith("--"):
            print(f"未知参数: {arg}")
            sys.exit(1)
        else:
            date_str = arg
    if not filepath:
        filepath = find_report(date_str)
    if not filepath:
        print("❌ 未找到报告文件")
        sys.exit(1)
    print(f"📄 报告文件: {filepath}")
    report_date, stocks = parse_report(filepath)
    print(f"📅 报告日期: {report_date}")
    print(f"📊 解析到 {len(stocks)} 只股票:")
    for s in stocks:
        print(f"  {s['code']} {s['name']}: 评分 {s['score']} | {s['trend']} | {s['action']}")
    inserted, rows = write_scores(report_date, stocks)
    print(f"\n✅ 写入完成: {inserted} 条新增")
    for r in rows:
        print(f"  {r['code']} {r['name']:8s} 评分 {int(r['score']):3d}  {r['trend']:4s}  {r['action']}")


if __name__ == "__main__":
    main()
