# LM Studio Model Variant Detection — Deep Debugging

This reference covers a recurring scenario: a GGUF file is placed in `~/.lmstudio/models/` via external download (aria2c, hf CLI, manual copy), validated as valid GGUF format, but LM Studio does not list it as a selectable variant — or a previously-seen variant (e.g. Q4) goes missing after cache edits.

## Architecture Overview

LM Studio has a **three-tier model state** that must stay in sync:

| Tier | Location | Role |
|------|----------|------|
| **GGUF Files** | `~/.lmstudio/models/<user>/<model>/*.gguf` | The actual model weights |
| **Hub Registration** | `~/.lmstudio/hub/models/<user>/<model>/` | Virtual model definition (manifest.json + model.yaml) |
| **Download Tracking** | `~/.lmstudio/.internal/download-jobs-info.json` | Records what was downloaded and its completion status |

When LM Studio starts, it does NOT do a fresh filesystem scan of all `*.gguf` files. Instead, it:

1. Reads hub registrations → determines what models exist
2. Reads download-jobs-info.json → determines completion status
3. Scans only verified files → builds model-index-cache.json + gguf-metadata-cache.json

**A GGUF file on disk that is not referenced by steps 1-2 is invisible to LM Studio.**

## Diagnosis Commands

```bash
# 1. Check GGUF file exists and is valid
ls -lh ~/.lmstudio/models/<user>/<model>/*.gguf
head -c 4 ~/.lmstudio/models/<user>/<model>/<file.gguf> | xxd
# Expect: 4747 5546 = "GGUF"

# 2. Verify the virtual model hub registration
cat ~/.lmstudio/hub/models/<user>/<model>/manifest.json
cat ~/.lmstudio/hub/models/<user>/<model>/model.yaml

# 3. Check download tracking for the specific model
python3 -c "
import json
dji = json.load(open('$HOME/.lmstudio/.internal/download-jobs-info.json'))
for j in dji.get('jobs', []):
    name = j.get('jobName', '')
    if '<user>' in name.lower() or '<model>' in name.lower():
        print(f'Found job: {name}')
        for t in j.get('tasks', []):
            filename = t.get('request', {}).get('subpath', '')
            dl = t.get('download', {})
            print(f'  Task: {filename} -> {dl.get(\"status\", \"?\")}')
"

# 4. Check model-index-cache
python3 -c "
import json
data = json.load(open('$HOME/.lmstudio/.internal/model-index-cache.json'))
for m in data.get('models', []):
    ident = m.get('indexedModelIdentifier', '')
    if '<user>' in ident.lower() or '<model>' in ident.lower():
        print(f'{ident}')
        print(f'  entryPoint: {m.get(\"entryPoint\",{}).get(\"filename\")}')
        print(f'  quant: {m.get(\"quant\",{})}')
"

# 5. Check gguf-metadata-cache
python3 -c "
import json
data = json.load(open('$HOME/.lmstudio/.internal/gguf-metadata-cache.json'))
for entry in data.get('json', {}).get('map', []):
    path = entry[0]
    if '<user>' in path.lower() or '<model>' in path.lower():
        info = entry[1].get('metadata', {})
        print(f'{path}')
        print(f'  arch: {info.get(\"arch\")}')
        print(f'  name: {info.get(\"name\")}')
"

# 6. Check model-data.json (load history + transitive status)
python3 -c "
import json
try:
    data = json.load(open('$HOME/.lmstudio/.internal/model-data.json'))
    for entry in data.get('json', []):
        name = entry[0]
        if '<user>' in name.lower() or '<model>' in name.lower():
            print(f'{name}')
            print(f'  transitive: {entry[1].get(\"transitive\", \"?\")}')
            print(f'  source: {entry[1].get(\"source\", \"none\")}')
except FileNotFoundError:
    print('model-data.json does not exist (fresh state)')
"
```

## What Does NOT Work

Documented failed attempts from real sessions:

### ❌ Clearing caches alone
```bash
rm -f ~/.lmstudio/.internal/model-index-cache.json
rm -f ~/.lmstudio/.internal/gguf-metadata-cache.json
rm -f ~/.lmstudio/.internal/model-data.json
```
LM Studio rebuilds all caches from hub registration + download tracking on next startup. If the Q8 variant was never downloaded through LM Studio's download system, it won't appear regardless of cache state.

### ❌ Manually inserting entries into model-index-cache.json
LM Studio overwrites the cache on startup with its own data. Hand-written entries are discarded.

### ❌ Changing entryPoint in model-index-cache.json
Even if the entryPoint points to Q8, LM Studio's resolution logic uses its own variant selection, not the cache file's value.

### ❌ Fake download record in endedDownloadsMap alone
Adding a Q8 entry to `single-downloads-info.json` or to `download-jobs-info.json["endedDownloadsMap"]` is insufficient. LM Studio's job system checks the `jobs[]` array first; `endedDownloadsMap` is secondary.

### ❌ Placing GGUF in a different directory
LM Studio only scans `~/.lmstudio/models/` and hub-registered paths.

### ❌ Using symlinks or hardlinks
LM Studio follows real paths and cross-checks with its metadata. Symlinks are resolved before comparison.

### ❌ The API `/api/v1/models/load` with raw file path
The API only accepts model identifiers that are already in the UI's model list. Direct GGUF paths are rejected.

### ❌ Completely removing hub virtual model registration
This causes LM Studio to show "没有模型可以选择了" / "No models available" because the virtual model is the only way LM Studio presents models to the user. The GGUF files on disk are visible to the backend but LM Studio has no UI-level model representation for them.

### ❌ Injecting Q8 as an additional task in the Qwen download job
Even if you add a Q8 task to `download-jobs-info.json["jobs"][].tasks[]` and update `taskIndexMapping`, LM Studio may not pick it up because the hub manifest.json's `fileNameFilter` must match, and the download job's `additionalIndexedModelIdentifiers` must include the Q8 identifier.

### ❌ Removing the unwanted variant (e.g. Q4) from disk
LM Studio detects the missing file and re-downloads it silently from HuggingFace if the hub virtual model registration still exists. The re-downloaded file may differ in size from the original (observed: 19.72 GB vs original 21.2 GB).

## What Works

### ✅ Use LM Studio's UI variant dropdown
If the Q8 file is in the correct directory and the caches are intact, the model appears in the model list. Click the model name → see a variant dropdown → select Q8_0. This is the intended UI path. The API has no programmatic way to switch variants.

### ✅ Use LM Studio's built-in download
The most reliable path. Search for the model in LM Studio's Model Hub and click Download. The file ends up in the right place with correct download tracking, caches, and hub registration.

### ✅ Use llama-server directly (bypass LM Studio UI)
LM Studio's llama.cpp backends can be launched independently:
```bash
~/.lmstudio/extensions/backends/llama.cpp-linux-arm64-nvidia-cuda13-2.23.1/llama-server \
  -m /path/to/Qwen3.5-35B-A3B-Q8_0.gguf \
  --port 1235 \
  -ngl 100 \
  --flash-attn on
```
This runs a separate HTTP server on port 1235 with the Q8 model loaded, completely bypassing LM Studio's model management. Use it via the OpenAI-compatible endpoint at `http://127.0.0.1:1235/v1`.

### ✅ Partial Fix: fileNameFilter + fake download record
See the (e) procedure in the main `lm-studio` skill's "Model not showing in UI" pitfall. This combines:
- manifest.json `fileNameFilter` to restrict what the hub expects
- Fake download entry in `download-jobs-info.json`
- Cache clearing

This approach can make the model appear in the UI but is fragile — applies only to the specific case where the hub registration is intact but a variant needs to be swapped.

## Root Cause Summary

LM Studio is designed as a **managed model environment**, not a raw GGUF file browser. Every GGUF file must be "introduced" through LM Studio's download system. Files placed by external means (aria2c, hf CLI, rsync) will never appear in the UI unless:

1. The hub virtual model registration points to them (manifest.json/model.yaml)
2. The download tracking system has a completion record for them (download-jobs-info.json)
3. The caches are then built from (1) and (2)

This is not a bug — it's a design choice. The canonical fix is to use LM Studio's own download, or to bypass the UI entirely with `llama-server`.
