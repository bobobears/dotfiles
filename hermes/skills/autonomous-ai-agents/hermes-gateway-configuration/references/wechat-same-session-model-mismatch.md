# WeChat: Same-Session Model Mismatch Diagnosis

## Symptom

- WeChat user receives error message (e.g., jinja template error) instead of a proper reply
- Gateway logs (`gateway.log`) show `response ready` and `Sending response (N chars)` — the reply was generated and sent
- `agent.log` shows the model used was **not** the expected cloud provider (e.g., DeepSeek), but a local/experimental model (Qwen, LM Studio)
- The error is the local model failing to render Hermes' prompt template

## Root Cause Chain (Full Trace)

```
User sends WeChat message
  → gateway.run: inbound message (platform=weixin)
    → get_or_create_session() → returns existing session entry (not expired)
      → _resolve_session_agent_runtime()
        → _resolve_gateway_model() reads config.yaml > model.default
          → Returns Qwen model (because global model.default was switched)
        → No channel override → returns Qwen config
      → AIAgent created with Qwen model
        → chat_completion: Qwen (LM Studio) fails with jinja error
          → 3 retries → all fail
            → Error response sent back to WeChat user
```

## Key Evidence

**gateway.log** (inbound → sent — notice: no actual error, looks successful):
```
INFO  gateway.run: inbound message: platform=weixin msg='<user text>'
INFO  gateway.run: response ready: platform=weixin time=8.5s api_calls=1 response=333 chars
INFO  gateway.platforms.base: [Weixin] Sending response (332 chars) ...
```

**agent.log** (model used & error — the real problem):
```
INFO  [<session_id>] run_agent: OpenAI client created ... model=qwen/qwen3.6-27b provider=deepseek base_url=http://127.0.0.1:1234/v1
INFO  [<session_id>] agent.chat_completion_helpers: Streaming failed before delivery: Error rendering prompt with jinja template: "No user query found in messages."
```

## Diagnostic Workflow

### Step 1: Confirm it's a model issue, not a channel issue

```bash
# Check if WeChat channel is actually connected
grep "weixin" ~/.hermes/logs/gateway.log | grep -i "connected\|inbound\|disconnected" | tail -5

# Check the model used for the latest WeChat message
grep "OpenAI client created" ~/.hermes/logs/agent.log | grep weixin | tail -3
```

If the model column shows `qwen/...` or `base_url=http://127.0.0.1:1234/v1` → **model routing issue**.

### Step 2: Find the exact chat_id for the override

```bash
grep "inbound message.*weixin" ~/.hermes/logs/gateway.log | grep -oP "chat=\S+" | head -1
```

### Step 3: Check jinja template error specifically

```bash
grep "jinja\|jinja2\|No user query\|template" ~/.hermes/logs/agent.log | tail -5
```

If found → the model (Qwen on LM Studio) doesn't understand Hermes' prompt template format.

### Step 4: Verify config.yaml model settings

```bash
hermes config get model
grep -A4 "weixin:" ~/.hermes/config.yaml | head -5
```

If `model.default` is `qwen/...` and there's no `channel_overrides` entry → fix by adding one.

### Step 5: After applying channel_overrides fix, verify it worked

```bash
# Check agent.log for the correct provider
grep "OpenAI client created" ~/.hermes/logs/agent.log | grep weixin | tail -3
```

Expected: `provider=deepseek` with the correct base_url (NOT `http://127.0.0.1:1234/v1`)

## The "Same Session Key" Trap

WeChat and TUI **can share a session key** when the TUI session was created from the same WeChat user context. The session key is:

```
agent:main:weixin:dm:<wechat_user_id>@im.wechat
```

If the TUI ran `/model qwen/qwen3.6-27b`, that writes the override to `_session_model_overrides[session_key]` — and the next WeChat message through **the same session_key** picks up that override.

## Fix

**Use `channel_overrides` with the exact chat_id.** The `platforms.weixin.model` config key does NOT work in current Hermes versions.

```yaml
# in ~/.hermes/config.yaml
platforms:
  weixin:
    enabled: true
    channel_overrides:
      'o9cq803nqghkYPUiUWjMHdtAvMgo@im.wechat':  # Exact chat_id from gateway.log
        model: deepseek-chat
        provider: deepseek
```

Set via CLI:
```bash
hermes config set platforms.weixin.channel_overrides.'<exact_chat_id>'.model 'deepseek-chat'
hermes config set platforms.weixin.channel_overrides.'<exact_chat_id>'.provider 'deepseek'
```

**⚠️ `channel_overrides` does NOT support wildcards.** `'*':` will NOT match any chat. You must use the exact chat_id.

**⚠️ `base_url` is NOT needed in `channel_overrides`.** The `provider` field is sufficient — `_resolve_runtime_agent_kwargs_for_provider()` resolves the correct base_url from the provider name.

### Verification After Fix

1. Restart gateway: `systemctl --user restart hermes-gateway`
2. Check agent.log for the correct provider:
```bash
grep "OpenAI client created" ~/.hermes/logs/agent.log | grep weixin | tail -3
```
Expected: `provider=deepseek` (NOT `provider=custom` or `base_url=http://127.0.0.1:1234/v1`)

## Prevention

When you run `/model <name>` in TUI to switch to a local model, also set `channel_overrides` for WeChat channels to always use the production model.

## One-Line Test

```bash
grep "OpenAI client created" ~/.hermes/logs/agent.log | grep weixin | tail -3
```

If the output shows `base_url=http://127.0.0.1:1234/v1` instead of the DeepSeek endpoint, the channel override is not active — add the `channel_overrides` entry.
