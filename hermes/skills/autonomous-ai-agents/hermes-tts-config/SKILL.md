---
name: hermes-tts-config
description: "Configure Hermes TTS voices and local Piper speech."
version: 1.0.0
author: agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [tts, voice, piper, edge-tts, china-network, audio]
---

# Hermes TTS Configuration

Configure and troubleshoot text-to-speech in Hermes Agent. Covers the built-in providers (edge default, local Piper), Chinese voice selection, and China-network workarounds for downloading Piper voice models.

## When to use

- User asks what TTS is / whether a local engine is installed
- Changing the default voice or provider (`tts.provider`, `tts.edge.voice`, `tts.piper.voice`)
- Installing a local/offline TTS engine (Piper) as an edge-tts fallback
- Piper voice download fails from mainland China

## Current setup on this machine (2026-08)

| Item | Value |
|------|-------|
| Default provider | `edge`, voice `zh-CN-XiaoxiaoNeural`（晓晓） |
| Local engine | piper-tts 1.6.0 in the hermes-agent venv |
| Piper voice | `zh_CN-huayan-medium`, cached at `~/.hermes/cache/piper-voices/` |

## Check what is installed

```bash
# CLI engines (usually none on a fresh box)
for cmd in espeak-ng piper flite festival; do command -v $cmd || echo "no $cmd"; done
# Hermes venv packages + config
pip list --path ~/.hermes/hermes-agent/venv/lib/python3.11/site-packages | grep -iE "tts|piper"
grep -A 5 "^tts:" ~/.hermes/config.yaml
```

Hermes' built-in providers: `edge` (default, free, online), `elevenlabs`, `openai`, `minimax`, `mistral`, `gemini`, `neutts`/`kittentts`/`piper` (local). The `text_to_speech` tool accepts a per-call `provider=` override, so you can keep edge as default and use piper offline without changing config.

## Change the edge voice

```bash
hermes config set tts.edge.voice zh-CN-XiaoxiaoNeural
# verify with a real generation: text_to_speech(text="测试", output_path=/tmp/t.mp3)
```

Useful Chinese voices: `zh-CN-XiaoxiaoNeural`（晓晓，女）, `zh-CN-YunxiNeural`（云希，男）, `zh-CN-XiaoyiNeural`（晓伊，活泼女）, `zh-CN-YunjianNeural`（云健，沉稳男）.

## Install Piper (local, offline)

1. **Install into the hermes-agent venv** — `_check_piper_available()` imports `piper` from that interpreter, so a system-wide install is invisible to Hermes:
   ```bash
   cd ~/.hermes/hermes-agent && uv pip install piper-tts --python venv/bin/python
   ```
2. **Get the voice model into the cache dir** — both `<voice>.onnx` and `<voice>.onnx.json` must exist in `~/.hermes/cache/piper-voices/`. When both are present, Hermes' resolver skips its own downloader entirely (this is how you bypass huggingface.co from China).
3. **Configure**: `hermes config set tts.piper.voice <voice-name>` (e.g. `zh_CN-huayan-medium`).
4. **Verify with real output** — never claim success on file size alone:
   ```
   text_to_speech(provider="piper", text="金医生你好，这是本地 Piper 引擎生成的语音。", output_path="/tmp/tts-test-piper.mp3")
   ```

## China-network voice download (the main gotcha)

The bundled `python -m piper.download_voices` hardcodes `huggingface.co`, which is unreachable from mainland China. Download manually from **hf-mirror.com** with the identical path structure, into `~/.hermes/cache/piper-voices/`. The exact URL format (including a 404-inducing path pitfall), how to enumerate available voices per language via `voices.json`, and the full working command for zh_CN are in `references/piper-voice-download-china.md` — read it before downloading any voice.

## Pitfalls

- **lang_family ≠ locale**: the first URL segment is the language *family* (`zh`), not the locale code (`zh_CN`). Using `zh_CN/huayan/...` returns 404; `zh/zh_CN/huayan/medium/...` works.
- **Cache dir may not exist** — `mkdir -p ~/.hermes/cache/piper-voices/` before downloading (Hermes only creates it lazily on first real use).
- **A 15-byte "download" is a 404 body**, not a model — check file size after curl; a medium voice is ~60MB.
- **piper-tts in the wrong venv** = provider silently unavailable to Hermes even though `pip show piper-tts` succeeds elsewhere.
- **voices.json is a dict keyed by voice name** (not a list of objects) — filter *keys* by language prefix to find voices per language.
- Piper Chinese catalog is small: only `zh_CN-huayan-medium`, `zh_CN-huayan-x_low`, `zh_CN-chaowen-medium`, `zh_CN-xiao_ya-medium`. Quality is a tier below edge-tts; keep edge as default, piper as offline fallback.

## Verification checklist

1. `hermes config set` output confirms the key landed in `~/.hermes/config.yaml`
2. A real `text_to_speech` call returns `success: true` with a non-trivial file size (tens of KB for a sentence)
3. Play/deliver the audio so the user hears it — voice choice is subjective, let them judge
