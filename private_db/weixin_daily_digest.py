#!/usr/bin/env python3
"""
微信每日摘要生成器
- 整理当天消息、文件、待办
- 生成中文摘要并推送
"""

import sqlite3
import os
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = os.path.expanduser("~/private_db/weixin.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def extract_todos_from_text(text):
    """从文本中提取待办事项"""
    todos = []
    if not text:
        return todos

    # 匹配常见的待办模式
    patterns = [
        r'请\s*(?:帮我|协助)?\s*(.{1,50})',
        r'需要\s*(?:做|处理|完成)\s*(.{1,50})',
        r'待\s*办[:：]?\s*(.{1,50})',
        r'要\s*(?:做|处理|完成)\s*(.{1,50})',
        r'记得\s*(?:要|做|处理)\s*(.{1,50})',
        r'提醒\s*(?:一下|你)?[:：]?\s*(.{1,50})',
        r'安排\s*(.{1,50})',
        r'准备\s*(.{1,50})',
        r'提交\s*(.{1,50})',
        r'发送\s*(.{1,50})',
        r'回复\s*(.{1,50})',
        r'确认\s*(.{1,50})',
        r'检查\s*(.{1,50})',
        r'修改\s*(.{1,50})',
        r'更新\s*(.{1,50})',
    ]

    for pattern in patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            todo_text = match.group(1).strip().rstrip('。！？!.?')
            if todo_text and len(todo_text) > 2:
                todos.append(todo_text)

    # 去重
    return list(dict.fromkeys(todos))


def generate_daily_digest(date_str=None):
    """生成每日摘要"""
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')

    conn = get_db()

    # 查询当天消息
    messages = conn.execute("""
        SELECT * FROM messages
        WHERE date(timestamp) = ? OR date(received_at) = ?
        ORDER BY timestamp ASC
    """, (date_str, date_str)).fetchall()

    # 查询当天文件
    files = conn.execute("""
        SELECT * FROM files
        WHERE date(downloaded_at) = ?
        ORDER BY downloaded_at ASC
    """, (date_str,)).fetchall()

    # 查询待办
    pending_todos = conn.execute("""
        SELECT * FROM todos
        WHERE status = 'pending'
        ORDER BY priority DESC, created_at ASC
    """).fetchall()

    # 生成摘要
    summary_parts = []

    if messages:
        summary_parts.append(f"📬 今日消息: {len(messages)} 条")

        # 按用户分组
        user_messages = {}
        for msg in messages:
            user_id = msg['from_user_id']
            if user_id not in user_messages:
                user_messages[user_id] = []
            user_messages[user_id].append(msg)

        for user_id, user_msgs in user_messages.items():
            user_name = user_msgs[0]['from_user_name'] or user_id[:8]
            msg_count = len(user_msgs)
            has_media = any(m['media_type'] for m in user_msgs)
            media_icon = " 📎" if has_media else ""

            # 提取关键内容
            key_texts = []
            for m in user_msgs:
                text = m['text']
                if text and len(text) > 3:
                    key_texts.append(text[:50])

            if key_texts:
                summary_parts.append(f"  • {user_name} ({msg_count}条{media_icon}): {key_texts[0]}...")
            else:
                summary_parts.append(f"  • {user_name} ({msg_count}条{media_icon})")

    if files:
        summary_parts.append(f"📁 今日文件: {len(files)} 个")
        for f in files:
            size_kb = f['file_size'] / 1024 if f['file_size'] else 0
            summary_parts.append(f"  • {f['file_name']} ({size_kb:.1f}KB) - {f['file_type']}")

    # 提取待办
    all_todos = []
    for msg in messages:
        msg_todos = extract_todos_from_text(msg['text'])
        for todo_text in msg_todos:
            all_todos.append({
                'content': todo_text,
                'from_user': msg['from_user_name'] or msg['from_user_id'][:8],
                'message_id': msg['message_id'],
                'priority': 'high' if '紧急' in msg['text'] or '尽快' in msg['text'] else 'normal',
            })

    # 保存待办到数据库
    for todo in all_todos:
        conn.execute("""
            INSERT OR IGNORE INTO todos
            (message_id, from_user_id, from_user_name, content, priority, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', datetime('now'))
        """, (
            todo['message_id'],
            todo.get('from_user', ''),
            todo.get('from_user', ''),
            todo['content'],
            todo.get('priority', 'normal'),
        ))
    conn.commit()

    # 保存摘要
    summary_text = "\n".join(summary_parts) if summary_parts else "今日无新消息"
    todos_text = json.dumps([t['content'] for t in all_todos], ensure_ascii=False)

    conn.execute("""
        INSERT OR REPLACE INTO daily_digests
        (date, message_count, file_count, todo_count, summary, todos)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        date_str,
        len(messages),
        len(files),
        len(all_todos),
        summary_text,
        todos_text,
    ))
    conn.commit()
    conn.close()

    return {
        'date': date_str,
        'message_count': len(messages),
        'file_count': len(files),
        'todo_count': len(all_todos),
        'summary': summary_text,
        'todos': all_todos,
    }


def format_digest_for_push(digest):
    """格式化为推送消息"""
    parts = []
    parts.append(f"📋 微信消息日报 - {digest['date']}")
    parts.append("")

    if digest['message_count'] == 0 and digest['file_count'] == 0:
        parts.append("今日无新消息 🎉")
    else:
        parts.append(digest['summary'])
        parts.append("")

        if digest['todos']:
            parts.append("📌 今日待办:")
            for i, todo in enumerate(digest['todos'], 1):
                priority_icon = "🔴" if todo.get('priority') == 'high' else "⚪"
                parts.append(f"  {i}. {priority_icon} {todo['content']} (来自: {todo.get('from_user', '未知')})")
            parts.append("")

    parts.append(f"统计: 消息 {digest['message_count']} 条 | 文件 {digest['file_count']} 个 | 待办 {digest['todo_count']} 项")

    return "\n".join(parts)


if __name__ == "__main__":
    import sys

    date_str = sys.argv[1] if len(sys.argv) > 1 else None
    digest = generate_daily_digest(date_str)

    # 输出格式化的摘要
    print(format_digest_for_push(digest))

    # 也输出 JSON 供程序使用
    print("\n--- JSON ---")
    print(json.dumps(digest, ensure_ascii=False, default=str))
