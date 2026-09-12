# 企业微信 / WeCom Setup

Hermes supports two mutually independent WeCom integrations. Pick based on whether you can expose a public HTTPS endpoint.

| Mode | Auth | Needs public URL | Transport | Use when |
|------|------|------------------|-----------|----------|
| **智能机器人** (Smart Robot) | QR scan, auto-provisioned creds | **No** | Outbound WebSocket (`wss://openws.work.weixin.qq.com`) | Default. Any home/office box behind NAT |
| **自建应用回调** (Custom-app callback) | Corp ID + Agent ID + Secret, manually issued | **Yes** — HTTPS callback URL | Inbound HTTPS callback | You have a tunnel or a real public host |

## Mode A — 智能机器人 (recommended)

### Credentials

Written to `~/.hermes/.env`:

```
WECOM_BOT_ID=<bot id>
WECOM_SECRET=<secret>
```

### Enabling

```yaml
# ~/.hermes/config.yaml
platforms:
  wecom:
    enabled: true
    extra: {}
```

An empty `extra: {}` is fine — the env-seeding pass fills `bot_id` / `secret` into `extra` at load time.

### Bot identity (name / avatar / bio) — WeCom-side only

The 智能机器人's **display name, avatar, bio, role persona and welcome message are
not Hermes settings**. There is no such key anywhere in
`plugins/platforms/wecom/` or under `platforms.wecom.extra` — do not go hunting
for a rename knob in `config.yaml`. They are set on the WeCom side:

```
work.weixin.qq.com/wework_admin/frame
→ 安全与管理 → 管理工具 → 智能机器人 → <the bot> → 详情 → 右上角「小笔」编辑
```

Desktop-client path: 工作台 → 智能机器人 → 该机器人 → 设置. Hermes cannot
rename the bot remotely — hand the user this path instead of attempting it.

Consequences worth stating up front:

- **Renaming is display-only.** Bot ID and Secret are unchanged, so the pairing
  approval, the group allowlists (`group_allow_from` / `groups.<chatid>`), and any
  `channel_overrides` keep working — **no gateway restart needed**. Only if the
  user also edits the API-mode credentials on that same page must
  `~/.hermes/.env` be updated and the gateway restarted.
- The display name is **not** the agent's persona name (the identity in
  `SOUL.md`). Renaming one does not change the other, so a colleague-facing bot
  named 大卫 will still introduce itself as Hermes unless the persona is aligned
  too — raise that as an explicit follow-up decision rather than silently leaving
  the mismatch.

### Non-interactive provisioning (driving the QR flow yourself)

The interactive wizard renders a QR in a PTY. To provision headlessly:

1. Generate the authorization QR:

```bash
~/.hermes/hermes-agent/venv/bin/python -c "
import qrcode
qrcode.make('https://work.weixin.qq.com/ai/qc/gen?source=hermes&scode=<scode>').save('/tmp/qr.png')
"
```

2. Hand `qr.png` to the user (in the desktop app: `MEDIA:/tmp/qr.png`), plus the plain URL so they can open it inside 企业微信.
3. Poll `https://work.weixin.qq.com/ai/qc/query_result` until the scan completes and the payload carries the bot id + secret.
4. Write the creds into `~/.hermes/.env` via the Hermes env helper (dedupes existing keys) rather than appending raw lines.
5. **Delete the temp dir afterwards** — the scan result contains the secret in plaintext.

### Approval

DM policy defaults to `pairing`. The user's first inbound message produces:

```
Hi~ I don't recognize you yet!
Here's your pairing code: XXXXXXXX
```

Approve with:

```bash
hermes pairing approve wecom XXXXXXXX
```

Messages that arrive **before** approval are logged as `Unauthorized user: <id> (<id>) on wecom` and dropped — that is expected, not a bug. Ask the user to send one more message afterwards to confirm the round-trip.

### Verification

```bash
grep -i wecom ~/.hermes/logs/gateway.log | tail -20
```

A healthy first connect looks like:

```
INFO gateway.run: Connecting to wecom...
INFO hermes_plugins.wecom_platform.adapter: [Wecom] Connected to wss://openws.work.weixin.qq.com
INFO gateway.run: ✓ wecom connected
```

And a verified round-trip:

```
INFO gateway.run: inbound message: platform=wecom user=<id> chat=<id> msg='...'
INFO gateway.run: response ready: platform=wecom chat=<id> time=2.8s api_calls=1 response=33 chars
```

Also check `~/.hermes/gateway_state.json` → `platforms.wecom.state == "connected"`.

### Notes

- `chatid=None`, `chattype='single'` in `Inbound callback:` lines is normal for 1:1 WeCom chats; the sender id doubles as the chat id and the session key is `agent:main:wecom:dm:<userid>`.
- Replies stream directly to the client, so `gateway.log` may log `Suppressing normal final send ... final delivery already confirmed (content_delivered=True)` instead of a separate outbound line. That means the reply landed — it is not a suppressed response.
- `[Wecom] Unrouted websocket payload dropped: cmd='(empty)' req_id=ping-…` every ~30s is harmless heartbeat noise.

## Mode B — 自建应用回调 (deferred / blocked for NAT-only hosts)

Hard prerequisite: a **publicly reachable HTTPS** callback URL registered in the WeCom admin console.

Why it fails on a typical Chinese home connection:

- Residential broadband blocks inbound 80/443.
- A stacked router topology (e.g. `192.168.31.149 → 192.168.31.1 → 192.168.10.1 → 192.168.1.1`) means port-forwarding must be configured on every hop, and the public IP is usually dynamic anyway.
- WeCom requires HTTPS — a bare-IP HTTP endpoint is rejected.

Workable options, in order of effort:

1. **Cloudflare Tunnel** — outbound-only tunnel, automatic HTTPS, arbitrary NAT traversal, and good ARM64 support. The usual best fit.
2. **frp / other reverse tunnel** to a cheap VPS.
3. Move the gateway to a host with a real public address.

Implementation reference: `plugins/platforms/wecom/callback_adapter.py` (reads corp id / agent id / callback token + encoding AES key).
