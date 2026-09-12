# WeCom (企业微信) 智能机器人 — 群聊接入

For the 智能机器人 (WebSocket long-connection) adapter in
`plugins/platforms/wecom/adapter.py`. Everything here is about getting the bot
useful **inside a WeCom group chat**, and about the two traps that cost real
time.

## What the bot can and cannot do in a group

Established from the official 帮助 page and the adapter source — state these to
the user *before* promising anything:

| Capability | Reality |
|---|---|
| Being added to a group | **User action only.** Hermes cannot do it. Mobile: 群聊 → 右上角群图标 → 添加成员 → 选择「智能机器人」. Desktop: 群聊 → 右上角带「+」的头像 → 「智能机器人」 |
| Which groups | **Internal (内部) groups only.** Interconnected / 上下游 / 外部 groups are not supported. Groups containing WeChat or other-org members will not accept the bot. |
| Receiving messages | **@mention only.** The bot sees messages in which it is @'d, not the group firehose. There is no "read everything" mode. |
| Replying | **Passive reply only.** Group sends require a cached inbound `req_id`; the adapter logs `No req_id available for group chat (passive reply required)` and refuses an unsolicited push. So cron jobs / alerts cannot target a WeCom group through this adapter. |
| 会话存档 | Group ↔ 智能机器人 chats are **not** captured by 会话内容存档. |

For push-only into a group (reports, alerts), the right tool is the classic
**群机器人 webhook** (群设置 → 群机器人 → 添加 → copy the webhook URL): any group
member can create it, no auth for the POST, works from a plain `curl` in cron.
That is a *different* mechanism from the 智能机器人 and does not need Hermes.

## Config surface

All keys live under `platforms.wecom.extra` and are read **once in `__init__`**,
so **any change requires a gateway restart** to take effect:

```yaml
platforms:
  wecom:
    enabled: true
    extra:
      group_policy: allowlist          # see below
      group_allow_from: [<group-chatid>]   # required only when group_policy=allowlist
      groups:
        "*":                            # wildcard default for unlisted groups
          allow_from: "bobobears"       # sender userids allowed to trigger, comma string OK
        <group-chatid>:
          allow_from: ["userid1", "userid2"]
```

`group_policy` values, and what the **code** actually does (see
`_is_group_allowed` in `adapter.py`):

| Value | Effect |
|---|---|
| `disabled` | all group messages dropped |
| `pairing` | **all group messages dropped** — there is no group pairing flow |
| `allowlist` | only group ids in `group_allow_from` pass |
| `open` | any group passes, then the per-group sender `allow_from` gate applies |

Semantics worth knowing:
- **The code default is `pairing`**, not `open` as the docs claim
  (`website/docs/user-guide/messaging/wecom.md` is stale here). Treat an unset
  `group_policy` as "all groups dropped".
- `_resolve_group_cfg` falls back to the `"*"` entry, so
  `groups: {"*": {allow_from: ...}}` is a global sender gate.
- `_coerce_list` splits a comma-separated string, so `allow_from: "a,b"` works
  as a list — `group_allow_from` behaves the same, and
  `hermes config set platforms.wecom.extra.group_allow_from "<chatid>" --force`
  stores it as a bare string. That is fine; do not hand-build a YAML list.
- `_entry_matches([], x)` is always False → an `allowlist` policy with an empty
  `group_allow_from` drops everything (fail-closed), which is a safe resting
  state while you discovery the group id.

## Per-group persona / self-name (`channel_overrides`)

The WeCom adapter does **not** implement `channel_prompts` (grep it — zero hits,
unlike feishu/discord/slack). Per-channel persona still works, because the
override is applied at the **gateway** layer, keyed by `chat_id`:

```yaml
platforms:
  wecom:
    channel_overrides:
      "<group-chatid>":          # plain scalar unless it contains @ or :
        system_prompt: "..."
```

Semantics (from `gateway/run_config_loaders.py::_get_system_prompt_for_channel`
and `gateway/run_turn_runner.py::_combined_ephemeral_prompt`):

- Lookup key is `ctx.source.chat_id` → on a group turn that is the **group
  chatid**, so one entry scopes the persona to exactly that group. There is **no
  wildcard**: an unlisted group/chat falls through to the global default.
- A set `system_prompt` **replaces the ephemeral layer** (`agent.system_prompt`
  / `display.personality`) — *not* `SOUL.md`. SOUL.md (identity, prompt slot #1)
  still applies everywhere. Check the global ephemeral prompt first
  (`hermes config get agent.system_prompt`, `hermes config get display.personality`);
  if it is empty the override costs nothing.
- It is combined **additively** with the platform-context prompt and the legacy
  adapter `channel_prompt`, so platform formatting hints survive.
- Values are bound at boot (`self.config`) → **restart the gateway** after writing.
- `channel_overrides` is a generic `PlatformConfig` field that also carries
  `model` / `provider` / `base_url`. Do not assume it is Discord-only because the
  docs example is — this deployment already uses it for a weixin DM.

Typical use: give a colleague-facing group a display identity distinct from the
operator's — group `system_prompt: "你是「大卫」…面向同事一律自称「大卫」，不要自称 Hermes"`
while DMs to the operator keep the default persona. Colleagues' **DMs** are a
different chat_id, so when you open DM access to someone new, add their override
in the same commit or they will self-identify as Hermes.

The same field is the right home for **channel-scoped rules** — a 办公群 that must
stay work-only (`不讨论私人事务，不提及股票/投资/理财`), a channel where a
different tone or language is required. Prefer this over asking the agent to
"remember": the override is injected on every turn for that channel, survives
restarts, and cannot be forgotten mid-conversation.

## Renaming the bot

The name / avatar / 简介 shown in WeCom live **entirely on the WeCom side**: the
plugin has no `bot_name` / `display_name` / `avatar` key (grep → zero hits).
Rename via 管理后台 → 安全与管理 → 管理工具 → 智能机器人 → 详情 → 右上角小笔
(desktop client: 工作台 → 智能机器人 → 设置).

Changing only the display name leaves **Bot ID / Secret unchanged**, so pairing,
`group_allow_from` and any `channel_overrides` keys stay valid — no gateway
restart needed. Only if you re-issue credentials do you touch `~/.hermes/.env`
and restart. The WeCom display name is *not* the agent's persona name: keep them
consistent deliberately (see the section above).

## Trap 1 — `open` refuses to start the whole gateway

Hermes has a **gateway-level startup guard** (`gateway/run.py`, the
`_own_policy_open_startup_violation` check). If any platform has `dm_policy` or
`group_policy` set to `open` while neither `GATEWAY_ALLOW_ALL_USERS=true` nor the
platform-specific `*_ALLOW_ALL_USERS` is set, the gateway **refuses to start**:

```
ERROR gateway.run: Refusing to start: wecom has dm_policy/group_policy set to
'open' but neither GATEWAY_ALLOW_ALL_USERS nor WECOM_ALLOW_ALL_USERS is enabled.
ERROR gateway.run: Gateway exiting cleanly: wecom: open policy without allow-all opt-in
```

Under systemd this becomes a **crash loop**, which also takes every other
platform (feishu/weixin/…) offline. Do not reach for `open` as a shortcut — use
`allowlist`, or set the allow-all env var deliberately. `allowlist`, `pairing`
and `disabled` all pass the guard.

## Trap 2 — discovering the group id is silent-but-logged

The adapter logs **every** inbound callback *before* the access-policy check, so
the group id and the sender's userid are in the log even while the message is
dropped for policy reasons:

```bash
search_files pattern="Inbound callback" path=~/.hermes/logs/gateway.log
# or grep the line:  Inbound callback: chattype='group' chatid='<group-chatid>' sender='<userid>'
```

So the safe sequence for a fresh group is **two steps, never a guess**:

1. Leave `group_policy: allowlist` with an empty `group_allow_from` (fail-closed).
   Have the user add the bot to the group and @mention it once.
2. Read `chatid` and `sender` from the log, then set
   `group_allow_from: [<chatid>]` + `groups.<chatid>.allow_from: [<sender>]`,
   restart, and have them @mention again to confirm a live reply.

Do **not** pre-fill the sender allowlist with a guessed userid: in group
callbacks `body.from.userid` is returned in plaintext only when the bot creator
is a super admin, otherwise it is an encrypted string. Confirm it from the log
rather than assuming.

## Verifying a change

```bash
hermes config set platforms.wecom.extra.<key> <value> --force   # nested dotted keys OK
systemctl --user show hermes-gateway -p MainPID --value        # PID must stay constant
awk '$0 >= "<start-ts>"' ~/.hermes/logs/gateway.log | grep -E "connected|Refusing to start"
```

Expect `Gateway running with N platform(s)` plus a `✓ wecom connected` line, and
**zero** occurrences of `Refusing to start`. `hermes gateway status` also prints
the Main PID and recent journal lines. Changing config does not itself restart
the service — call `hermes gateway restart` (it briefly drops the WS, reconnects
in ~2s, and interrupts any running cron job).

Then prove the *group* round-trip, not just connectivity — have the user @mention
the bot once more and check that a single healthy exchange leaves all four lines:

```
<ts> Inbound callback: chattype='group' chatid='<group-chatid>' sender='<userid>'
<ts> Batched ... session=agent:main:wecom:group:<group-chatid>:<userid>
<ts> gateway.run: inbound message: platform=wecom ... msg='<their text>'
<ts> gateway.run: response ready: platform=wecom ... time=Ns content_delivered=True
```

- `content_delivered=True` with **no** separate outbound line is success, not a
  suppressed send — group replies stream straight to the client (see
  `wecom-setup.md` Notes).
- Zero `DROPPED` entries after your start timestamp is the proof the allowlist
  matched; `awk '$0 >= "<start-ts>"' ~/.hermes/logs/gateway.log | grep -c DROPPED`
  is the quick check.
- Group and DM sessions are **separate contexts**:
  `agent:main:wecom:group:<chatid>:<sender>` in a group vs
  `agent:main:wecom:dm:<userid>` in 1:1 — the same person has two independent
  histories. Say this before the user trips over it.
- The `msg=` field is the text with the @mention already stripped, so a
  `msg=''` line means the user @'d the bot without typing anything.
