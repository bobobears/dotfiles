# Piper voice download from mainland China (hf-mirror)

Validated working path, 2026-08. The bundled downloader (`python -m piper.download_voices`) hardcodes `huggingface.co` — unreachable from CN. Bypass it by curling the same files from **hf-mirror.com** into Hermes' cache dir; when both `<voice>.onnx` and `<voice>.onnx.json` exist there, Hermes' `_resolve_piper_voice_path()` skips its own downloader entirely.

## URL format (from piper's download_voices source)

```
https://huggingface.co/rhasspy/piper-voices/resolve/main/{lang_family}/{lang_code}/{voice_name}/{quality}/{lang_code}-{voice_name}-{quality}{ext}?download=true
```

Swap the host for `hf-mirror.com`. **Pitfall: `{lang_family}` is NOT the locale.** For Chinese it is `zh`, not `zh_CN`:

- ❌ `.../main/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx` → 404
- ✅ `.../main/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx` → works

Other families follow the same pattern: `en/en_US/lessac/medium/...`, `de/de_DE/thorsten/medium/...`.

## Enumerate available voices for a language

The repo's `docs/VOICES.md` only lists languages, not voice names. The authoritative list is `voices.json`:

```bash
curl -sL "https://hf-mirror.com/rhasspy/piper-voices/resolve/main/voices.json?download=true" -o /tmp/piper-voices.json
python3 -c "
import json
d = json.load(open('/tmp/piper-voices.json'))   # DICT keyed by voice name, not a list
zh = {k: v for k, v in d.items() if k.startswith('zh_')}
for name in zh: print(name)
"
```

Known zh_CN voices (2026-08): `zh_CN-huayan-medium`, `zh_CN-huayan-x_low`, `zh_CN-chaowen-medium`, `zh_CN-xiao_ya-medium`. That's the whole Chinese catalog — quality is a tier below edge-tts.

## Working download command (zh_CN example)

```bash
mkdir -p ~/.hermes/cache/piper-voices && cd ~/.hermes/cache/piper-voices
for f in zh_CN-huayan-medium.onnx zh_CN-huayan-medium.onnx.json; do
  curl -sL --max-time 300 \
    "https://hf-mirror.com/rhasspy/piper-voices/resolve/main/zh/zh_CN/huayan/medium/$f?download=true" \
    -o "$f"
done
ls -lh   # .onnx should be ~60MB for medium quality
```

Then: `hermes config set tts.piper.voice zh_CN-huayan-medium` and verify with a real `text_to_speech(provider="piper", ...)` call.

## Failure signatures seen in the wild

| Symptom | Cause | Fix |
|---------|-------|-----|
| 15-byte files after curl | 404 body saved as file (wrong path) | Check URL segments; lang_family is `zh` not `zh_CN` |
| `{"error":"zh_CN does not exist on \"main\""}` from HF API tree endpoint | Same path confusion, via the API instead of resolve URLs | Use `{lang_family}/{lang_code}/...` in both |
| Download "succeeds" but Hermes says voice missing | Only one of `.onnx` / `.onnx.json` present | Both files are required — download them as a pair |
| `piper.download_voices` hangs/times out from CN | Hardcoded huggingface.co | Don't use it; curl hf-mirror directly (above) |
