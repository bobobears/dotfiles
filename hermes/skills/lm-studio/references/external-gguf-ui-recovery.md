# External GGUF → LM Studio UI — Verified Completion Recipe

Session-verified 2026-08-17: Qwen3.8-27B Q4_K_M downloaded from ModelScope was made to appear in the LM Studio UI and load successfully. This file documents the FINAL steps (4–6) that `api-download-and-modelscope-fallback.md` left pending, plus the kill pitfall that cost an hour.

## Prerequisite

Steps 1–3 of `api-download-and-modelscope-fallback.md` completed: API download started (state tiers created), byte-identical files pulled from ModelScope into `/tmp/ms-model-dl`, sha256 verified against `download-jobs-info.json` → `tasks[].request.sha256`.

## ⚠️ Kill pitfall (the hour-loser)

`pkill -f "LM-Studio.AppImage"` does NOT kill the app. The AppImage runtime executes as:

```
/tmp/.mount_LM-StuXXXX/lm-studio
```

so an AppImage-name pattern matches nothing. The old process keeps running and its in-memory download state **overwrites any hand-edited JSON** on restart (observed: `download-jobs-info.json` flipped back from `completed` to `transferring` with progress climbing).

**Correct kill:**
```bash
pkill -f "\.mount_LM-Stu.*/lm-studio"; sleep 5
ps aux | grep -iE "lm.studio|mount_LM" | grep -v grep || echo "stopped"
```
(`killall -9 lm-studio` also works.) Always verify the process is gone BEFORE editing `~/.lmstudio/.internal/*.json`.

## Step 4 — Place files

```bash
# Remove partial-download residue
rm -f ~/.lmstudio/models/lmstudio-community/*/lmstudio-community/<repo>/*.part

# Move ModelScope files into the savePath final names (same filesystem → instant mv)
mv /tmp/ms-model-dl/*.gguf ~/.lmstudio/models/lmstudio-community/<parent>/lmstudio-community/<repo>/

# Verify sha256 of BOTH files against the job's request.sha256
sha256sum ~/.lmstudio/models/lmstudio-community/<parent>/lmstudio-community/<repo>/*.gguf
```

`<parent>` is whatever dir LM Studio's `savePath` nests under — do NOT "fix" the nesting (known path-management quirk).

## Step 5 — Update BOTH state files to completed

LM Studio reads both files; editing only one gets overwritten.

**`~/.lmstudio/.internal/download-jobs-info.json`** — the `jobs[]` array:
```python
for j in dji.get('jobs', []):
    for t in j.get('tasks', []):
        dl = t.get('download', {})
        if '<repo>' in json.dumps(t).lower():
            dl['status'] = 'completed'
            dl['downloadedSizeBytes'] = dl['totalSizeBytes']
```

**`~/.lmstudio/.internal/single-downloads-info.json`** — CRITICAL: `downloadsMap` entries are **`[identifier, {...}]` tuples, NOT dicts**:
```python
for dl in d.get('downloadsMap', []):
    # dl is a 2-element list: [identifier_string, status_dict]
    entry = dl[1] if isinstance(dl, list) else dl
    if '<repo>' in json.dumps(dl).lower():
        entry['status'] = 'completed'
```

## Step 6 — Restart and verify

```bash
~/LM-Studio.AppImage --no-sandbox   # in Hermes: terminal(background=true), no &
sleep 45                            # first scan takes ~30-45s

lms ls                              # model key = short form, e.g. qwen3.8-27b
lms load "qwen3.8-27b"              # loads in ~8s on GB10 for 16.8GB Q4_K_M
# chat-completion smoke test:
curl -s -m 120 -X POST http://127.0.0.1:1234/api/v0/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.8-27b","messages":[{"role":"user","content":"hi"}],"max_tokens":50}'
```

Notes:
- `lms load` uses the SHORT key (`qwen3.8-27b`), NOT the full path from `/api/v1/models`.
- The native `/api/v1/models` returns models under the `models` key (not `data`) — check with `lms ls` if the API shape confuses you.
- Verify with `lms ls` BEFORE trusting the API; the CLI shows what the UI shows.
