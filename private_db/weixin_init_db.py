"""初始化微信消息数据库"""
import sqlite3
import os

DB_PATH = os.path.expanduser("~/private_db/weixin.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 消息表
    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id TEXT UNIQUE,
        from_user_id TEXT,
        from_user_name TEXT,
        chat_type TEXT,  -- 'dm' or 'group'
        chat_id TEXT,
        text TEXT,
        media_type TEXT,  -- 'image', 'video', 'audio', 'file', 'voice', NULL
        media_count INTEGER DEFAULT 0,
        timestamp TEXT,
        received_at TEXT DEFAULT (datetime('now')),
        is_processed INTEGER DEFAULT 0,
        summary TEXT
    )
    """)

    # 文件表
    c.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id TEXT,
        file_name TEXT,
        file_path TEXT,
        file_type TEXT,
        file_size INTEGER,
        from_user_id TEXT,
        from_user_name TEXT,
        download_status TEXT DEFAULT 'pending',  -- 'pending', 'downloaded', 'failed'
        downloaded_at TEXT,
        FOREIGN KEY (message_id) REFERENCES messages(message_id)
    )
    """)

    # 待办事项表
    c.execute("""
    CREATE TABLE IF NOT EXISTS todos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id TEXT,
        from_user_id TEXT,
        from_user_name TEXT,
        content TEXT,
        priority TEXT DEFAULT 'normal',  -- 'high', 'normal', 'low'
        status TEXT DEFAULT 'pending',  -- 'pending', 'completed', 'cancelled'
        due_date TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        completed_at TEXT,
        FOREIGN KEY (message_id) REFERENCES messages(message_id)
    )
    """)

    # 每日摘要表
    c.execute("""
    CREATE TABLE IF NOT EXISTS daily_digests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT UNIQUE,
        message_count INTEGER DEFAULT 0,
        file_count INTEGER DEFAULT 0,
        todo_count INTEGER DEFAULT 0,
        summary TEXT,
        todos TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)

    # 轮询状态表
    c.execute("""
    CREATE TABLE IF NOT EXISTS poll_state (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at TEXT DEFAULT (datetime('now'))
    )
    """)

    # 创建索引
    c.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_messages_from_user ON messages(from_user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat_type ON messages(chat_type)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_files_message_id ON files(message_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_todos_status ON todos(status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_todos_created ON todos(created_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_digests_date ON daily_digests(date)")

    conn.commit()
    conn.close()
    print(f"数据库已初始化: {DB_PATH}")

if __name__ == "__main__":
    init_db()
