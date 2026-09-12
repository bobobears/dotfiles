# WeChat Message Monitoring via Hooks

Complete workflow for monitoring WeChat messages, tracking files, and generating daily digests using Hermes Gateway's Hook system.

## Architecture

```
WeChat → iLink Bot → Hermes Gateway → Hook (agent:start) → SQLite DB
                                                ↓
                                         Cron Job (18:00) → Digest → Push
```

## Components

### 1. Database Schema (`~/private_db/weixin.db`)

Tables:
- `messages` — inbound message log (message_id, from_user_id, text, media_type, timestamp)
- `files` — file tracking (message_id, file_name, file_path, download_status)
- `todos` — extracted action items (content, priority, status, due_date)
- `daily_digests` — daily summary archive (date, message_count, file_count, summary)
- `poll_state` — polling state persistence

### 2. Hook Handler (`~/.hermes/hooks/weixin-message-logger/handler.py`)

Key implementation details:
- `handle(event_type, context)` receives both sync and async calls
- Filter by `context.get("platform") == "weixin"` to only process WeChat messages
- On `agent:start`: insert message into `messages` table
- On `agent:end`: optionally log the agent's response
- Media files: parse `gateway.log` for `media=N` entries and cross-reference with `~/.hermes/cache/` files

### 3. Daily Digest Script (`~/private_db/weixin_daily_digest.py`)

- Runs daily at 18:00 via Cron Job
- Queries today's messages, files, and todos from the database
- Extracts action items from message text using regex patterns (请, 需要, 待办, 记得, etc.)
- Outputs formatted Chinese summary
- Also outputs JSON for programmatic use

## Setup Steps

1. Initialize database:
```bash
python3 ~/private_db/weixin_init_db.py
```

2. Create hook directory and files (see SKILL.md "Message Monitoring via Hooks" section)

3. Restart gateway:
```bash
systemctl --user restart hermes-gateway
```

4. Verify hook loaded:
```bash
journalctl --user -u hermes-gateway --since "1 minute ago" | grep "Loaded hook"
```

5. Create daily digest Cron Job:
```
Cron Job name: 微信每日摘要
Schedule: 0 18 * * *
Deliver: origin,all
Toolsets: terminal
```

## Important Notes

- **Hook errors never block the pipeline** — if `handler.py` throws, the message still reaches the agent
- **iLink Bot limitation**: Bot mode only sees messages sent TO the bot, not all WeChat conversations
- **Media tracking is indirect**: The Hook only gets text. Files are tracked by monitoring `~/.hermes/cache/images/`, `~/.hermes/cache/audio/`, `~/.hermes/cache/documents/` and cross-referencing with gateway.log `media=N` entries
- **Sync buffer conflict**: Do NOT run a separate poller that also calls `ilink/bot/getupdates` — it will conflict with the gateway's sync buffer and cause messages to be lost
- **Message text is truncated to 500 chars** in the Hook context. For full text, parse gateway.log directly

## Troubleshooting

- Hook not firing: Check `journalctl --user -u hermes-gateway | grep "Loaded hook"` after restart
- Messages not appearing in DB: Check `handler.py` for Python errors in gateway logs
- Media files not tracked: Verify `~/.hermes/cache/` directories exist and have recent files
- Digest shows "今日无新消息": Messages may have been received before the Hook was installed — they won't be retroactively captured
