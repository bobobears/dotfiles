# Qwen on LM Studio - Jinja Template Error

## Error Message

```
Error rendering prompt with jinja template: "No user query found in messages."
```

## Root Cause

When the global model is set to Qwen via LM Studio (`http://127.0.0.1:1234/v1`), the model fails to render Hermes' prompt template. This is a **model compatibility issue** — Qwen's prompt template format differs from what Hermes expects.

## Symptoms

- Gateway shows platform as "connected"
- `gateway.log` shows "response ready" and "Sending response"
- But user receives: `⚠️ The model provider failed after retries. I kept raw provider details out of chat; check gateway logs for diagnostics.`
- `agent.log` shows repeated jinja template errors with 3 retries

## Diagnostic Commands

```bash
# Check which model/base_url is being used for the platform
grep "OpenAI client created" ~/.hermes/logs/agent.log | grep weixin | tail -3

# Expected BAD output (local LM Studio):
# provider=deepseek base_url=http://127.0.0.1:1234/v1 model=deepseek-v4-flash

# Expected GOOD output (DeepSeek cloud):
# provider=deepseek base_url=https://api.deepseek.com/v1 model=deepseek-chat
```

## Fix

Set `channel_overrides` with the **exact chat_id** AND **explicit base_url**:

```yaml
platforms:
  weixin:
    enabled: true
    channel_overrides:
      'o9cq803nqghkYPUiUWjMHdtAvMgo@im.wechat':
        model: deepseek-chat
        provider: deepseek
        base_url: https://api.deepseek.com/v1
```

### Why `base_url` is required

Even with `provider: deepseek`, if the global `model.base_url` is set to `http://127.0.0.1:1234/v1`, the resolved runtime will use that endpoint. The `base_url` field in `channel_overrides` ensures the correct API endpoint is used regardless of global config.

### Code changes needed

If `base_url` is not working in `channel_overrides`, the `ChannelOverride` dataclass may need updating:

1. Add `base_url` field to `gateway/config.py`:
```python
@dataclass
class ChannelOverride:
    model: Optional[str] = None
    provider: Optional[str] = None
    system_prompt: Optional[str] = None
    base_url: Optional[str] = None  # Add this
```

2. Update `from_dict()` and `to_dict()` to handle `base_url`

3. Add to `gateway/run.py` in `_resolve_session_agent_runtime()`:
```python
if ch.base_url:
    runtime_kwargs["base_url"] = ch.base_url
```

## Alternative Solutions

1. **Switch global model to cloud provider**: `hermes config set model.base_url 'https://api.deepseek.com/v1'`
2. **Use a different local model** that supports Hermes' prompt template
3. **Configure LM Studio with a compatible prompt template** (advanced)

## Related

- `references/wechat-same-session-model-mismatch.md` — Cross-session model confusion
- Main skill: `autonomous-ai-agents/hermes-gateway-configuration`
