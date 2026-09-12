# Desktop model routing mismatch (HTTP 400)

## Error transcript

Desktop launches but every API call fails with mismatched provider + model:

```
[hermes] ⚠️  API call failed (attempt 1/3): BadRequestError [HTTP 400]
[hermes]    🔌 Provider: deepseek  Model: qwen/qwen3.6-27b
[hermes]    🌐 Endpoint: https://api.deepseek.com/v1
[hermes]    📝 Error: HTTP 400: The supported API model names are deepseek-v4-pro or deepseek-v4-flash, but you passed qwen/qwen3.6-27b.
```

## Root cause

Desktop's internal `hermes serve` backend resolves provider and model independently. When `config.yaml` has:
- `model.provider: lmstudio` (with `model.default: qwen/qwen3.6-27b`)
- `delegation.provider: deepseek` (with `delegation.model: deepseek-v4-flash`)

The serve backend can pick the DeepSeek endpoint from `delegation` but the model name from `model.default`, causing a 400.

## Diagnosis

```bash
# Check what config.yaml says:
hermes config get model
hermes config get delegation

# Check what the desktop backend actually used:
grep 'Provider:' ~/.hermes/logs/desktop.log | tail -5
```

## Resolution

Ensure `model.provider`, `model.default`, and `model.base_url` are all consistent:

```bash
# Option A: Use DeepSeek (recommended for production)
hermes config set model.provider deepseek
hermes config set model.default deepseek-v4-flash
hermes config set model.base_url https://api.deepseek.com/v1

# Option B: Use LM Studio (local only)
hermes config set model.provider lmstudio
hermes config set model.default qwen/qwen3.6-27b
hermes config set model.base_url http://127.0.0.1:1234/v1
```

Then restart the desktop app:
```bash
~/.hermes/hermes-agent/venv/bin/hermes desktop --skip-build
```

## Session note (2026-07-31)

This was discovered when the user reported "HTTP 400: The supported API model names are deepseek-v4-pro or deepseek-v4-flash, but you passed qwen/qwen3.6-27b" in the desktop app. The `model` config was set to LM Studio but the desktop serve backend was routing to DeepSeek. Fixing `model.provider` to `deepseek` resolved it.
