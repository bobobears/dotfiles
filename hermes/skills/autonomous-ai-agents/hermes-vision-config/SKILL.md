---
name: hermes-vision-config
description: Configure, troubleshoot, and switch Hermes Agent vision (auxiliary.vision) providers — local LM Studio multimodal models, SiliconFlow API, OpenRouter, and other OpenAI-compatible endpoints.
version: 1.0.0
author: Hermes
tags: [hermes, vision, auxiliary, configuration, troubleshooting]
---

# Hermes Vision Configuration

Configure Hermes Agent's image recognition capability (`vision_analyze` tool).

## How Vision Works

- When the main model lacks native vision (e.g. DeepSeek), Hermes falls back to `auxiliary.vision` config
- `vision_analyze` tool sends the image to the configured vision provider
- Result is returned as text description to the main model

## Configuration Commands

```bash
hermes config set auxiliary.vision.provider <provider>
hermes config set auxiliary.vision.model <model_name>
hermes config set auxiliary.vision.base_url <api_endpoint>
```

## Provider Options

### Option 1: SiliconFlow (硅基流动, Recommended for Chinese users)

SiliconFlow provides OpenAI-compatible multimodal models.

```bash
hermes config set auxiliary.vision.provider openai
hermes config set auxiliary.vision.base_url https://api.siliconflow.cn/v1
hermes config set auxiliary.vision.model Qwen/Qwen2-VL-7B-Instruct
```

Add to `~/.hermes/.env`:
```
SILICONFLOW_API_KEY=sk-xxxxxxxxxxxx
```

Other compatible SiliconFlow vision models:
- `Qwen/Qwen2-VL-72B-Instruct` (better quality, slower)
- `Qwen/Qwen2.5-VL-7B-Instruct` (newer)
- `deepseek-ai/deepseek-vl2` (DeepSeek visual)

### Option 2: Local LM Studio (Local, Free)

Only works with **multimodal/vision** models. Text-only models (e.g. `qwen3.6-27b`) will fail with:
```
unknown variant `image_url`, expected `text`
```

Requires a VL (Vision-Language) model, e.g.:
- `qwen2.5-vl-7b-instruct` (GGUF)
- `Qwen2-VL-7B` (GGUF)
- `llava-v1.6-*` (GGUF)

```bash
hermes config set auxiliary.vision.provider openai
hermes config set auxiliary.vision.base_url http://127.0.0.1:1234/v1
hermes config set auxiliary.vision.model <vision-model-name>
```

### Option 3: OpenRouter

```bash
hermes config set auxiliary.vision.provider openrouter
# or
hermes config set auxiliary.vision.provider openai
hermes config set auxiliary.vision.base_url https://openrouter.ai/api/v1
hermes config set auxiliary.vision.model google/gemini-2.0-flash-001
```

Requires `OPENROUTER_API_KEY` in `.env`.

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `No LLM provider configured for task=vision` | auxiliary.vision not set | Configure provider/model/base_url |
| `unknown variant 'image_url', expected 'text'` | Model doesn't support vision (text-only) | Switch to a VL model |
| `400 Bad Request` | API endpoint incompatible | Use OpenAI-compatible endpoint |
| `401 Unauthorized` | Missing API key | Add key to `.env` |
| Timeout | Network issue or model too slow | Try smaller model, check network |

## Verification

Run `vision_analyze` on any image to test. Success = text description returned. Failure = error message with details.

## Critical Notes

- **User preference**: BoboBears prefers local-first (LM Studio) for cost, falls back to SiliconFlow when local lacks capability. Don't default to paid cloud APIs without asking.
- Config changes take effect **immediately** — no restart needed
- The vision provider is independent from the main model provider
- SiliconFlow is the preferred option for users in China (fast, uses existing account)
- When switching between local and cloud vision providers, only `base_url` and `model` need changing
