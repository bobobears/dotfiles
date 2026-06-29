# Weixin / WeChat Gateway Setup

Connects Hermes Agent to personal WeChat accounts via the Tencent iLink Bot API.

## Architecture

Hermes uses the [iLink Bot API](https://ilinkai.weixin.qq.com) as the bridge to WeChat. The adapter:
- Polls for messages via HTTP long-poll (35s timeout, not WebSocket)
- Sends/receives text, images, videos, files (all with AES-128-ECB CDN encryption)
- Shows typing indicators in WeChat
- Renders Markdown natively

## Prerequisites

```bash
pip install aiohttp cryptography qrcode
```

All three are needed for the Weixin adapter to start and for QR code rendering.

## Setup Steps

### 1. Run the Setup Wizard

```bash
hermes gateway setup
```

Because the wizard uses interactive terminal UI, run it as:

```bash
# In Hermes session:
terminal(command="hermes gateway setup", background=true, pty=true)
# Then:
process(action="submit", data="3", session_id="xxx")  # Select Weixin
process(action="submit", data="Y", session_id="xxx")  # Confirm QR login
```

### 2. Scan the QR Code

- The terminal displays a QR code (requires `qrcode` package)
- Also prints a URL like: `https://liteapp.weixin.qq.com/q/...?bot_type=3`
- User scans with phone WeChat → "扫一扫"
- QR auto-refreshes up to 3 times if it expires

### 3. Auto-Configuration

After scanning, the wizard automatically saves to `~/.hermes/.env`:

```
WEIXIN_ACCOUNT_ID=<ilink_bot_account_id>
WEIXIN_TOKEN=<ilink_bot_token>
```

### 4. Complete & Start Gateway

After WeChat setup, select "Done" in the wizard, then start the gateway:

```bash
hermes gateway start
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WEIXIN_ACCOUNT_ID` | ✅ | — | iLink Bot account ID (from QR login) |
| `WEIXIN_TOKEN` | ✅ | — | iLink Bot token (auto-saved from QR login) |
| `WEIXIN_BASE_URL` | — | `https://ilinkai.weixin.qq.com` | iLink API base URL |
| `WEIXIN_CDN_BASE_URL` | — | `https://novac2c.cdn.weixin.qq.com/c2c` | CDN base URL for media |
| `WEIXIN_DM_POLICY` | — | `open` | DM access: `open`, `allowlist`, `disabled`, `pairing` |
| `WEIXIN_GROUP_POLICY` | — | `disabled` | Group access: `open`, `allowlist`, `disabled` |
| `WEIXIN_ALLOWED_USERS` | — | _(empty)_ | Comma-separated user IDs for DM allowlist |
| `WEIXIN_GROUP_ALLOWED_USERS` | — | _(empty)_ | Comma-separated **group chat IDs** (not user IDs) |
| `WEIXIN_HOME_CHANNEL` | — | — | Chat ID for cron/notification output |

## Config.yaml Entry

```yaml
platforms:
  weixin:
    enabled: true
```

Already present after setup wizard completes.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `WEIXIN_TOKEN is required` | Re-run `hermes gateway setup` to scan QR code |
| `aiohttp and cryptography are required` | `pip install aiohttp cryptography` |
| QR code not rendering | `pip install qrcode` |
| Session expired (`errcode=-14`) | Re-run `hermes gateway setup`, scan new QR |
| Bot doesn't respond | Check `WEIXIN_DM_POLICY` — if `allowlist`, sender must be in `WEIXIN_ALLOWED_USERS` |
| Group messages ignored | Group policy defaults to `disabled`. QR-login bot identities (`...@im.bot`) typically can't receive group events at all |
| `Another local Hermes gateway is already using this token` | Only one poller per token allowed. Stop other gateway first |

## Features

- **Text**: Markdown rendering preserved (headers, tables, code fences)
- **Images**: AES-encrypted CDN transfer, decrypted automatically
- **Video**: Download, decrypt, cache as MP4
- **Voice**: Extracts transcription if available, otherwise caches SILK audio
- **Typing indicators**: Shown in WeChat while processing
- **Message chunking**: 4000-char limit, splits at logical boundaries
- **Context tokens**: Disk-backed per-peer, survives gateway restarts

## Official Docs

https://hermes-agent.nousresearch.com/docs/user-guide/messaging/weixin
