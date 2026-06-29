# Feishu / Lark Gateway Setup

Connects Hermes Agent to Feishu (飞书) / Lark via the Feishu Open Platform bot API. Supports WebSocket mode for real-time messaging.

## Architecture

Hermes creates a Feishu custom bot via the Open Platform. The adapter:
- Connects via **WebSocket** (real-time, no polling)
- Sends/receives text, images, files, and voice messages
- Shows typing indicators in Feishu
- Handles group @mentions

**Important:** The setup wizard can auto-create the bot via QR code scan — you don't need to manually create a Feishu app.

## Prerequisites

The gateway auto-installs `lark-oapi` when Feishu is configured. No manual pip install needed in most cases.

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
process(action="submit", data="10", session_id="xxx")   # Select Feishu / Lark
process(action="submit", data="1", session_id="xxx")    # Select "Scan QR code to create new bot"
```

### 2. Choose Setup Method

The wizard offers two options:
- **1. Scan QR code to create a new bot automatically** (recommended) — generates a QR code that opens the Feishu Open Platform launcher
- **2. Enter existing App ID and App Secret manually** — for pre-existing Feishu apps

### 3. Scan the QR Code

- The terminal displays a QR code (requires `qrcode` package)
- Also prints a URL like: `https://open.feishu.cn/page/launcher?user_code=XXXX&from=hermes&tp=hermes`
- User scans with phone Feishu → "扫一扫" or opens the URL in a browser
- After scanning, the wizard auto-creates the bot app on Feishu Open Platform

### 4. Auto-Configuration

After scanning, the wizard:
- Creates the Feishu bot automatically
- Saves credentials to `~/.hermes/.env` (FEISHU_APP_ID, FEISHU_APP_SECRET, etc.)
- Updates `~/.hermes/config.yaml` to enable the feishu platform

### 5. DM Policy & Group Settings

The wizard will ask:

**DM authorization:**
1. Use DM pairing approval (recommended) — unknown users request access, you approve with `hermes pairing approve`
2. Allow all direct messages
3. Only allow listed user IDs

**Group chats:**
1. Respond only when @mentioned in groups (recommended)
2. Disable group chats

**Home channel (optional):** Leave blank if you already have another platform as home channel for cron/notifications.

### 6. Complete & Restart Gateway

After Feishu setup, select "Done" in the wizard, then restart the gateway:

```bash
# The wizard asks: "Restart the gateway to pick up changes?" → Y
# Or manually:
hermes gateway restart
```

## Pairing Approval

After setup, the first user who DMs the bot will trigger a pairing request. Approve the user with:

```bash
hermes pairing approve feishu <pairing_code>
```

The pairing code is shown when the user sends their first message.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FEISHU_APP_ID` | ✅ | — | Feishu app ID (from auto-create or manual entry) |
| `FEISHU_APP_SECRET` | ✅ | — | Feishu app secret |
| `FEISHU_DOMAIN` | — | `feishu` | Domain: `feishu` for Chinese users, `lark` for international |
| `FEISHU_DM_POLICY` | — | `open` | DM access: `open`, `pairing`, `allowlist`, `disabled` |
| `FEISHU_GROUP_POLICY` | — | `mention` | Group access: `mention`, `open`, `disabled` |
| `FEISHU_ALLOWED_USERS` | — | _(empty)_ | Comma-separated user IDs for DM allowlist |
| `FEISHU_ALLOWED_GROUPS` | — | _(empty)_ | Comma-separated group chat IDs |

## Post-Setup Config Check

After the wizard completes, **verify the `config.yaml` platforms section** — two known issues can cause the gateway to crash on startup:

**Issue 1: Missing `enabled: true`**
The wizard may write only `home_channel:` under `platforms.feishu:` but omit `enabled: true`. Fix:
```bash
hermes config set platforms.feishu.enabled true
```

**Issue 2: `home_channel` stored as plain string instead of YAML dict**
The gateway expects a nested dict:
```yaml
platforms:
  feishu:
    enabled: true
    home_channel:
      platform: feishu
      chat_id: oc_0ceccf7646b77e9bde35e360953fe805
      name: Home
```

If `home_channel` is a plain string (e.g. `home_channel: oc_xxx`), the gateway crashes with `TypeError: string indices must be integers, not 'str'`. **Do NOT use JSON** with `hermes config set` — it stores the JSON as a literal string. Set sub-keys individually:
```bash
hermes config set platforms.feishu.home_channel.platform feishu
hermes config set platforms.feishu.home_channel.chat_id oc_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
hermes config set platforms.feishu.home_channel.name Home
```

Verify the result by reading the config:
```bash
hermes config show | grep -A5 feishu
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Gateway installs lark-oapi on first start | Normal — wait for pip install to complete |
| Bot doesn't respond in group | Must @mention the bot. Check `FEISHU_GROUP_POLICY` |
| Bot doesn't respond to DMs | Check `FEISHU_DM_POLICY`. If `pairing`, run `hermes pairing approve` |
| WebSocket connection fails | Check network/firewall. Feishu Open Platform must be reachable |
| Gateway crashes on startup: `TypeError: string indices must be integers, not 'str'` | Check `platforms.feishu.home_channel` format — must be a nested YAML dict, not a plain string. See "Post-Setup Config Check" above |
| Gateway responds to Feishu DMs but streams no chunks for minutes | Provider (e.g. LM Studio, local model) may respond HTTP 200 without actually streaming tokens. Test with `curl -N -X POST http://provider:port/v1/chat/completions -d '{"model":"model","messages":[{"role":"user","content":"hi"}],"stream":true}' \| head -5`. Switch provider to a cloud service (DeepSeek, OpenAI) if local inference is unresponsive |

## Features

- **Text**: Markdown rendering with headers, lists, code fences
- **Images**: Send/receive via Feishu's native attachment system
- **Files**: Document attachments supported
- **Voice**: Transcription supported
- **Typing indicators**: Shown in Feishu while processing
- **Group @mentions**: Responds only when mentioned (configurable)
- **WebSocket**: Real-time connection, no HTTP polling

## Official Docs

https://hermes-agent.nousresearch.com/docs/user-guide/messaging/feishu
