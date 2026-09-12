# Diagnosing the Cross-Session Error Illusion

A user reports seeing an error message in a messaging platform (WeChat, Feishu, Telegram) but the **gateway log shows the reply was sent successfully**. The error the user actually saw came from a different, parallel session.

## When This Pattern Applies

Hermes runs multiple concurrent sessions:
- **TUI (terminal UI)** — the local chat session using its own model provider
- **Gateway sessions** — each messaging platform (WeChat, Feishu, etc.) has its own session with its own provider
- **Cron job runs** — scheduled tasks in isolated sessions

When two sessions hit errors at the **same timestamp**, an error displayed in one place (e.g., the TUI terminal) can be **misattributed** to another channel (e.g., WeChat).

## Real Example

```
Time    TUI Session (Qwen local)          WeChat Gateway (DeepSeek)
──────  ─────────────────────────────      ─────────────────────────────
22:15:34                                    inbound received
22:15:37  inbound received (TUI)            
22:15:38  API FAIL 1/3 (jinja error)        inbound message processing
22:15:40  API FAIL 2/3                      
22:15:46  API FAIL 3/3 — ❌ FINAL ERROR     response ready (333 chars)
                                            sending response to WeChat
```

In this case, the `❌ API failed after 3 retries` error displayed in the **TUI** was visible to the user, while the **WeChat reply actually succeeded** (the gateway log confirms the response was sent).

## Diagnostic Workflow

### 1. Get the exact timestamp from the user's report

The user may not know the precise time, but approximate ("about 10pm yesterday") is enough to start searching.

### 2. Check gateway.log for the platform session

```bash
grep "22:1[5-9]" ~/.hermes/logs/gateway.log
```

Look for:
- `inbound message:` — the user's message was received
- `response ready:` — the response was generated
- `Sending response` — the response was dispatched to the platform adapter

If all three are present, the platform pipeline worked.

### 3. Check errors.log for parallel session failures

```bash
grep "22:1[5-9]" ~/.hermes/logs/errors.log
```

Look for ERROR entries at the **same timestamp**. Each ERROR has a session ID (`[20260706_002658_xxxxxx]`) — if the session ID differs from the gateway session, it's a parallel session failure.

### 4. Separate the two timelines

Key markers:
| Log Entry | Meaning |
|-----------|---------|
| `gateway.run: inbound message` | User message entered the agent |
| `gateway.run: response ready` | Agent generated a reply |
| `gateway.platforms.base: Sending response` | Reply dispatched to platform adapter |
| `agent.conversation_loop: API call failed` | A **different** session failed |
| `agent.conversation_loop: Retrying` | The failed session is retrying |

### 5. Check for provider/model mismatch

The TUI session and gateway session may use **different providers**:
- **TUI** might be configured to use `custom:lmstudio` (local Qwen)
- **Gateway** might use `deepseek` (cloud DeepSeek)

**Critical nuance:** `config.yaml` `model.default` is a **single global setting**. When the user runs `/model <local_model>` in the TUI, it rewrites `config.yaml`, which affects **every** platform, not just the TUI. The gateway has no per-platform model configuration — all inbound messages use the same `model.default`.

To distinguish which scenario you're in:

| If the gateway agent log shows... | Conclusion |
|-----------------------------------|-----------|
| `provider=deepseek` — WeChat works | Different providers per session. Local TUI failure does not affect gateway. |
| `provider=custom base_url=localhost` — WeChat gets jinja error too | Global model contamination. `/model` in TUI rewrote config.yaml for all platforms. |

To verify: `grep -A4 "^model:" ~/.hermes/config.yaml` shows the current global default.

**When the local model fails (jinja template, OOM, etc.), the TUI shows the error. Whether the gateway is affected depends on whether `model.default` points to the local model or the cloud model.**

## Common Parallel Session Failure Patterns

### Pattern A: LM Studio Jinja Error (Qwen GGUF)

**Symptom:** `Error rendering prompt with jinja template: "No user query found in messages."`

**When it fires:** First message in a fresh session using a Qwen GGUF model served by LM Studio. The Qwen GGUF's chat template misreads the conversation history format.

**Why it's confusing:** The user just typed a message, so "no user query" makes no sense — but the template is failing to detect the user message because of a role-sequence issue in the template engine.

**Recovery:** The error is self-limiting — it affects only the session using the local model. The TUI session recovers when restarted. See `lm-studio` skill for `killall` recovery if the inference engine hangs.

#### Sub-pattern A1: Cross-platform Model Config Contamination

**Symptom:** User receives jinja template error **on WeChat/Feishu**, not in the TUI. The error message says the same LM Studio jinja error, but the user sent the message from their phone, not the TUI terminal.

**Root cause:** `config.yaml` global `model.default` has been set to the local Qwen model (e.g. by running `/model qwen/qwen3.6-27b` in the TUI). The gateway reads this **single global config** for all platforms — there is no per-platform model config. Every inbound message from every platform uses what `model.default` says.

**Why it's not a routing error:** The session key (e.g. `agent:main:weixin:dm:...`) correctly resolves to the WeChat session. The `_should_reset` check passes. **The model choice is the issue, not the session routing.**

**Diagnostic checklist:**

| Check | What to look for |
|-------|------------------|
| `config.yaml model.default` | Is it set to a local model? (`qwen/qwen3.6-27b`, `lm-studio`, `custom`) |
| `grep session_key ~/.hermes/sessions/sessions.json` | Does the platform's session_key point to the same `session_id` as before? (If yes, routing is fine.) |
| Gateway log `OpenAI client created` | What `provider` and `base_url` does it show for the platform's turn? |
| Agent log `conversation turn` | What `model` and `provider` are logged for the platform? |
| TUI `/model` history | Was `/model <local_model>` executed recently, changing the global config? |

**Key evidence from a real case:**

```
# gateway.log: session routing is correct
session_key=agent:main:weixin:dm:o9cq803n@im.wechat
session_id=20260706_002658_c16c8f

# agent.log: the model used was the local one, not the expected cloud provider
conversation turn: session=20260706_002658_c16c8f model=qwen/qwen3.6-27b provider=custom platform=weixin

# sessions.json confirms the correct routing
"agent:main:weixin:dm:o9cq803n..." -> session_id: "20260706_002658_c16c8f"

# config.yaml contains the local model
model:
  default: qwen/qwen3.6-27b
  provider: custom
  base_url: http://127.0.0.1:1234/v1
```

**Fix:** Edit `config.yaml` to restore the intended model:

```bash
hermes model set deepseek-chat --provider deepseek
```

Or manually in `~/.hermes/config.yaml`:

```yaml
model:
  default: deepseek-chat
  provider: deepseek
  # remove any base_url / api_key that points to LM Studio
```

**Prevention:** There is currently no per-platform model config in Hermes gateway — `model.default` applies globally. Any `/model` command in the TUI changes the model for **every** platform. If you need different models for different platforms, consider keeping a separate profile or documenting that a `/model` switch will affect all channels until reverted.

### Pattern B: Rate-limited session (iLink WeChat)

**Symptom:** `ilink sendmessage rate limited`

**When it fires:** Multiple rapid messages in sequence.

**Gateway behavior:** The adapter self-throttles (backoff + circuit breaker) and recovers. The gateway log shows `backing off Xs before retry`, then `reset rate limit circuit` on success.

**Confusion:** If the TUI also hits a failure at the same time, the user may think the rate limit is the cause of TUI errors too.

### Pattern C: DNS failure (cascade)

**Symptom:** `NameResolutionError` / `Temporary failure in name resolution`

**Cascade:** A single router DNS failure can affect BOTH the gateway's outbound sends AND the provider API calls (DeepSeek, etc.) simultaneously.

**Confusion:** The user sees a provider API error (from TUI or cron) and a gateway send error at the same time, and assumes they're different root causes. They're not — fix DNS first. See `references/dns-troubleshooting.md` under `hermes-gateway-configuration`.

## Key Insight

**The error the user sees is not always the error they should be diagnosing.**

Always correlate the exact error message against the session ID and the platform before explaining what went wrong. If the gateway log shows success, the error belongs to a parallel session — not the messaging channel.
