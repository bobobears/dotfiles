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
| Send fails with `rate limited`, `errcode=-2` | Tencent-side throttle on the iLink bridge, not a Hermes fault. Raise the pacing/circuit knobs, and move scheduled notifications to Feishu — see §Rate Limiting |

## Rate Limiting (`errcode=-2`)

Log signature:

```
[Weixin] send failed to=<id>: iLink sendmessage rate limited; cooldown active for 30.0s
```

### What it is

`-2` comes back from the iLink service itself (`RATE_LIMIT_ERRCODE = -2` in `gateway/platforms/weixin.py`) — a Tencent-side frequency cap on this third-party bridge. It is undocumented, offers no quota dashboard and no `Retry-After`, and cannot be appealed. Nothing in Hermes removes it; you can only lower the trigger rate. Do not confuse it with `errcode=-14` (session expired → re-scan QR).

### Why the logs overstate it

On the first `-2` the adapter opens a circuit breaker (defaults: `rate_limit_circuit_threshold=1`, `…_window_seconds=30`, `…_open_seconds=30`). While it is open, every subsequent send fails immediately **in-process** — `raise RuntimeError("…cooldown active…")`, no network request — and each attempt logs its own ERROR line, including the automatic retry and the plain-text fallback send. So a single upstream throttle can produce several ERROR lines. Count **distinct cooldown starts**, not matching lines.

### What triggers it

- Several messages sent close together. Long replies are chunked (`_SPLIT_THRESHOLD = 1800`; iLink itself cuts at ~2048) with only `send_chunk_delay_seconds` between chunks.
- Bursts inside one wall-clock minute — gateway startup + shutdown notices, or several cron jobs delivering at the same 17:00/18:00 tick.
- Re-sending during an open breaker: retries cannot succeed and only add noise.

### Tunables

Set under `config.yaml → platforms.weixin.extra` (behavioural settings, deliberately not env vars). Read **once at adapter construction** — a gateway restart is required.

| Key | Default | Effect | Raise it when |
|-----|---------|--------|---------------|
| `send_chunk_delay_seconds` | 1.5 | Gap between chunks of one long reply | Long replies keep tripping the cap |
| `rate_limit_circuit_open_seconds` | 30.0 | How long the breaker stays open after a `-2` | You want failed sends to stop retrying at once and wait the throttle out |
| `rate_limit_circuit_window_seconds` | 30.0 | Window for counting events toward the threshold | Rarely — with `threshold=1` widening it changes nothing |
| `rate_limit_circuit_threshold` | 1 | Events needed to trip the breaker | Never; 1 is the safe value |

These keys contain no `@`, so `hermes config set` writes them directly:

```bash
hermes config set platforms.weixin.extra.send_chunk_delay_seconds 4.0
hermes config set platforms.weixin.extra.rate_limit_circuit_open_seconds 60.0
```

### Which delivery path is affected

Group the failures by what preceded them — the answer decides whether the fix is tuning (pacing) or routing (channel):

```bash
grep -c "rate limited" ~/.hermes/logs/gateway.log                                            # inflated total
grep "rate limited" ~/.hermes/logs/gateway.log | awk '{print $1}' | sort | uniq -c             # per-day spread
grep -B3 "rate limited" ~/.hermes/logs/gateway.log | grep -E "startup notification|Shutdown|Sending response"
```

Startup/shutdown notices and scheduled pushes dominate the hits; live replies are hit far less often. Automation traffic is therefore best **routed away** from iLink rather than merely paced.

### Prefer a documented channel for automation

Feishu publishes its limits (1000 messages/min, 50/s; 5 QPS to any single chat) and does not throttle at ordinary agent volume — its failure log contains connection timeouts and certificate errors only, never `rate limit`. Deliver cron output there (`deliver='feishu:<chat_id>'`) and keep WeChat for interactive use. Feishu's docs additionally advise avoiding the top of the hour and half-hour, when its system load spikes.

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
