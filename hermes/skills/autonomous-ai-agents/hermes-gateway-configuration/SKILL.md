---
name: hermes-gateway-configuration
description: "Configure, troubleshoot, and operate Hermes Agent messaging gateway platforms — Telegram, WeChat/Weixin, Discord, Slack, WhatsApp, and 20+ others."
version: 1.2.0
author: agent
created_by: agent
metadata:
  hermes:
    tags: [hermes, gateway, messaging, setup, configuration, platforms, weixin, wechat]
    homepage: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/
    related_skills: [hermes-agent]
platforms: [linux, macos, windows]
---

# Hermes Gateway Configuration

Configure messaging platform adapters for Hermes Agent's gateway system. The gateway is a single background process that connects all your configured platforms, handles sessions, runs cron jobs, and delivers responses.

## Trigger

Load this skill whenever the user asks to:
- Set up, configure, or connect a messaging platform (Telegram, WeChat/微信, Feishu/飞书, Discord, Slack, etc.)
- Troubleshoot a failing platform adapter
- Run or manage the gateway service
- "Connect Hermes to WeChat/微信/Telegram/Discord"

## Prerequisites

- Hermes Agent installed and configured
- `hermes doctor` passes (check before starting)
- Python packages may be needed per platform (see below)

## Workflow

### 1. Check Current Gateway Status

```bash
hermes gateway status
```

Shows whether the gateway is running, its PID, and which platform adapters are connected.

### 2. Run Interactive Setup Wizard

```bash
hermes gateway setup
```

This is an **interactive, non-pty-aware** wizard. To drive it programmatically (from within a Hermes session):

```bash
# Start in background mode with PTY
terminal(command="hermes gateway setup", background=true, pty=true)
# Then interact with process('submit')
process(action="submit", data="3", session_id="proc_xxx")  # select option 3
process(action="submit", data="Y", session_id="proc_xxx")  # confirm
```

**NOTE:** The wizard does NOT render correctly in plain foreground `terminal()` calls (exits with code 1). Always use `background=true + pty=true` and submit choices via `process(action='submit')`.

### 3. Platform-Specific Dependencies

Before running setup, ensure required Python packages are installed:

| Platform | Required pip packages |
|----------|----------------------|
| Weixin / WeChat | `aiohttp cryptography qrcode` |
| Feishu / Lark | Auto-installed (`lark-oapi`) |
| (Add more platforms as discovered) | |

Install with: `pip install aiohttp cryptography qrcode`

### 4. Follow Platform-Specific Setup

Each platform has specific steps after the wizard starts:

**Weixin / WeChat:**
1. Run `hermes gateway setup`, select WeChat (option 3, may vary)
2. Confirm `Y` to start QR login
3. A QR code appears in the terminal (requires `qrcode` package for proper rendering)
4. User must scan the QR code with their phone's WeChat app
5. A URL link is also provided as fallback if QR code rendering fails
6. After scanning, the wizard auto-saves `WEIXIN_ACCOUNT_ID` and `WEIXIN_TOKEN` to `~/.hermes/.env`

Full docs: `references/weixin-setup.md`

**Feishu / Lark:**
1. Run `hermes gateway setup`, select Feishu / Lark (option 10, may vary)
2. Select option 1: "Scan QR code to create a new bot automatically" (recommended)
3. A QR code appears in the terminal
4. User scans with Feishu phone app → the wizard auto-creates a bot
5. Wizard prompts: DM policy → Group policy → Home channel (optional)
6. The gateway may auto-install `lark-oapi` on first startup after configuration
7. After setup, approve the first user with `hermes pairing approve feishu <code>`

Full docs: `references/feishu-setup.md`

### 5. Complete Configuration

After the platform wizard finishes:
1. The wizard returns to the platform selection menu
2. Select "Done" (the last option)
3. The wizard will ask if you want to install/start the gateway service
4. Confirm to start the gateway, or start it later with:

```bash
hermes gateway run       # Foreground
hermes gateway install   # Install as user service
hermes gateway start     # Start service
```

### 6. Approve Users (Pairing Mode)

If you selected **DM pairing** during setup, the first message from each user triggers a pairing request. Approve them with:

```bash
hermes pairing approve <platform> <pairing_code>
```

Examples:
```bash
hermes pairing approve weixin NP4S2A26
hermes pairing approve feishu NP4XXXXX
```

After approval, the user is recognized automatically on their next message.

## Platform-Specific Reference Files

- `references/weixin-setup.md` — Full WeChat/Weixin setup details and troubleshooting
- `references/feishu-setup.md` — Full Feishu/Lark setup details and troubleshooting
- `references/dns-troubleshooting.md` — DNS resolution failure patterns for gateway platforms (especially behind China ISP routers)

## Verification

- After setup: `hermes gateway status` shows the platform as connected
- Send a test message from the platform to verify round-trip
- Check logs: `tail -f ~/.hermes/logs/gateway.log`

## Pitfalls

- **QR code not rendering**: The `qrcode` Python package must be installed. Without it, the wizard prints a URL link instead and `pip install qrcode` fixes it.
- **Interactive wizard in PTY mode**: `hermes gateway setup` must be run as a background process with `pty=true`. Foreground terminal() calls fail with exit code 1 because the wizard uses a terminal UI that doesn't work in pure pipe mode.
- **Session expiry**: WeChat iLink Bot sessions expire after a while (`errcode=-14`). Re-run `hermes gateway setup` to scan a new QR code.
- **Multiple gateway instances**: Only one poller per platform token is allowed. Stop the other gateway first.
- **Gateway config location**: Platform adapter config lives in `~/.hermes/.env` (secrets/credentials) and `~/.hermes/config.yaml` (enable/disable flags under `platforms:<name>:enabled`).
- **Pairing code is transient**: The pairing code shown in response to a user's first DM is one-time-use. If you didn't catch it, the user needs to send another message to generate a new code.
- **Feishu `lark-oapi` auto-install**: When the gateway starts after Feishu config, it auto-installs `lark-oapi` via pip. This adds ~30s to first startup. Subsequent startups are instant.
- **After adding a new platform, restart the gateway**: `hermes gateway restart` picks up new `.env` variables. The setup wizard offers this automatically.
- **Platform connected but replies not delivered**: If WebSocket/poll shows connected but outbound API calls fail with `NameResolutionError` / `Temporary failure in name resolution`, the system DNS server (often home router) is intermittently failing to resolve the platform's HTTP API domain. Fix with fallback public DNS + `/etc/hosts` entries. Full debugging workflow: `references/dns-troubleshooting.md`.
- **Cannot restart gateway from inside the gateway process**: `hermes gateway restart` and `systemctl --user restart` are blocked with "cannot restart or stop the gateway from inside the gateway process" (SIGTERM propagates to child processes). Instead, use `kill -9 <PID>` to force-stop; systemd auto-restarts it. Find the PID with `ps aux | grep 'python.*hermes.*gateway' | grep -v grep | grep -v slash_worker`.
- **Feishu `home_channel` must be a YAML dict, not a plain string**: After wizard setup, `platforms.feishu.home_channel` may be stored as a string rather than a nested dict. The gateway expects `{platform: feishu, chat_id: "oc_xxx", name: Home}`. `hermes config set` with a JSON string stores it as a literal string — set sub-keys individually: `hermes config set platforms.feishu.home_channel.platform feishu`, `hermes config set platforms.feishu.home_channel.chat_id oc_xxx`, `hermes config set platforms.feishu.home_channel.name Home`.
- **Feishu `platforms.feishu` may lack `enabled: true`**: The wizard may write the feishu platform section with only `home_channel:` but no `enabled: true`, causing a `TypeError` on startup. Fix: `hermes config set platforms.feishu.enabled true`.
- **Provider streaming timeouts cause the gateway to hang**: If the configured provider (e.g., LM Studio, local GGUF) responds HTTP 200 but never streams chunks, the gateway blocks until `gateway_timeout` (default 1800s per attempt × up to 3 retries = up to 90 min total). The user sees "⏳ Working — N min — iteration X/150, waiting for stream response". Test with `curl -N -s -X POST http://127.0.0.1:1234/v1/chat/completions -d '{"model":"model","messages":[{"role":"user","content":"hi"}],"stream":true}' | head -5` to verify streaming actually produces chunks. Switch to a cloud provider (DeepSeek, OpenAI, etc.) if local inference can't keep up.
