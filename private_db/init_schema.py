#!/usr/bin/env python3
"""初始化私人数据库：建表 + 填充自选股"""
import sqlite3
import os

DB_PATH = os.path.expanduser("~/private_db/private.db")

def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 按列名访问
    conn.execute("PRAGMA journal_mode=WAL")  # 性能优化
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def create_tables(conn):
    schema = """
    -- ==========================================
    -- 自选股列表
    -- ==========================================
    CREATE TABLE IF NOT EXISTS watchlist (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        code        TEXT    NOT NULL UNIQUE,         -- 股票代码 (6位)
        name        TEXT    NOT NULL,                 -- 股票名称
        added_date  TEXT    NOT NULL DEFAULT (date('now')),
        priority    INTEGER DEFAULT 0,               -- 排序权重，越大越靠前
        active      INTEGER DEFAULT 1,               -- 1=关注中, 0=已移除
        sector      TEXT,                             -- 所属板块/行业
        notes       TEXT                              -- 个人备注
    );

    -- ==========================================
    -- 交易记录
    -- ==========================================
    CREATE TABLE IF NOT EXISTS trades (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        code        TEXT    NOT NULL,
        trade_date  TEXT    NOT NULL,
        direction   TEXT    NOT NULL CHECK(direction IN ('buy', 'sell')),
        price       REAL    NOT NULL,
        shares      INTEGER NOT NULL,
        fees        REAL    DEFAULT 0,
        notes       TEXT,
        created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
    );

    -- ==========================================
    -- 分红记录
    -- ==========================================
    CREATE TABLE IF NOT EXISTS dividends (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        code                TEXT    NOT NULL,
        ex_date             TEXT    NOT NULL,          -- 除权除息日
        dividend_per_share  REAL    NOT NULL,           -- 每股分红（税前）
        pay_date            TEXT,                       -- 派息日
        notes               TEXT
    );

    -- ==========================================
    -- 个股笔记/研究
    -- ==========================================
    CREATE TABLE IF NOT EXISTS stock_notes (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        code        TEXT    NOT NULL,
        title       TEXT,
        content     TEXT,
        created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
    );

    -- ==========================================
    -- DSA 每日评分存档（自动导入用）
    -- ==========================================
    CREATE TABLE IF NOT EXISTS daily_scores (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        code        TEXT    NOT NULL,
        date        TEXT    NOT NULL,
        score       REAL,
        trend       TEXT,
        action      TEXT,
        UNIQUE(code, date)
    );

    -- 索引
    CREATE INDEX IF NOT EXISTS idx_trades_code     ON trades(code);
    CREATE INDEX IF NOT EXISTS idx_trades_date     ON trades(trade_date);
    CREATE INDEX IF NOT EXISTS idx_daily_code_date ON daily_scores(code, date);
    CREATE INDEX IF NOT EXISTS idx_notes_code      ON stock_notes(code);
    """
    conn.executescript(schema)
    conn.commit()
    print("✅ 表结构创建完成")

def populate_watchlist(conn):
    """填充 9 支自选股"""
    stocks = [
        ("002047", "宝鹰股份",     "建筑装饰", 90),
        ("688603", "XD天承科",     "电子",     85),
        ("300706", "阿石创",       "电子",     80),
        ("301228", "实朴检测",     "专业服务", 75),
        ("301392", "汇成真空",     "专用设备", 70),
        ("301306", "西测测试",     "专业服务", 65),
        ("300750", "宁德时代",     "电力设备", 60),
        ("002966", "苏州银行",     "银行",     55),
        ("002039", "黔源电力",     "公用事业", 50),
    ]
    inserted = 0
    for code, name, sector, priority in stocks:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO watchlist(code, name, sector, priority)
                VALUES (?, ?, ?, ?)
            """, (code, name, sector, priority))
            if conn.total_changes > inserted:
                inserted += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    print(f"✅ 自选股填充完成（{inserted} 支新增）")

def verify(conn):
    rows = conn.execute("""
        SELECT code, name, sector, priority, active
        FROM watchlist
        ORDER BY priority DESC
    """).fetchall()
    print(f"\n📋 当前自选股 ({len(rows)} 支)：")
    print(f"{'代码':<8} {'名称':<10} {'板块':<10} {'权重':<6} {'状态'}")
    print("-" * 50)
    for r in rows:
        status = "✅" if r["active"] else "⛔"
        print(f"{r['code']:<8} {r['name']:<10} {r['sector']:<10} {r['priority']:<6} {status}")

if __name__ == "__main__":
    conn = get_conn()
    create_tables(conn)
    populate_watchlist(conn)
    verify(conn)
    conn.close()
    print(f"\n📁 数据库位置: {DB_PATH}")
    print("💡 命令行快速查询: sqlite3 ~/private_db/private.db")
