# LM Studio Built-in Download via API + ModelScope Acceleration

Session-verified workflow (LM Studio 0.4.18, mainland China network, 2026-08-17) for getting an externally-placed GGUF to appear in the LM Studio UI **without** re-downloading through the slow official proxy.

## Context

A GGUF placed in `~/.lmstudio/models/` by aria2c/hf CLI never appears in the UI (three-tier state: disk files + hub registration + download tracking must all agree — see `model-variant-detection.md`). The canonical fix is LM Studio's own download. But LM Studio's built-in download goes through its proxy (`search.lmstudio.ai/v1/hf-proxy/...`) which is ~0.3 MB/s from mainland China → 13+ hours for a 16 GB quant. ModelScope mirrors the same `lmstudio-community` GGUF repos with **byte-identical files** at ~10 MB/s.

## The API call (this is what actually registers the model)

```bash
# ✅ Correct form: full HuggingFace URL, repo name LOWERCASED
curl -s -X POST http://127.0.0.1:1234/api/v1/models/download \
  -H "Content-Type: application/json" \
  -d '{"model":"https://huggingface.co/lmstudio-community/qwen3.8-27b-gguf"}'
# → {"job_id":"job_...","status":"downloading","total_size_bytes":...}
```

## Error forms that DO NOT work (all verified)

| Request body | Error |
|---|---|
| `{"repoType":"huggingface","owner":"...","repo":"..."}` | `Missing required field 'model'` |
| `{"model":"lmstudio-community/Qwen3.8-27B-GGUF"}` (bare owner/repo) | `Downloading community models as artifacts is not supported. Please use the HuggingFace model URL` |
| `{"model":"https://huggingface.co/lmstudio-community/Qwen3.8-27B-GGUF"}` (mixed-case repo) | HF canonicalizes to lowercase — use the lowercase URL the error suggests |

## Cancel endpoints — none exist

`POST /api/v1/models/download/cancel`, `POST /api/v1/jobs/cancel`, `DELETE /api/v1/models/download/<job>`, `GET /api/v1/downloads` → all `Unexpected endpoint or method`. To abort: kill LM Studio (`killall -9 lm-studio` or pkill the AppImage), remove `downloading_*.part` files.

## Default variant trap

LM Studio picks a default quant from the repo — for Qwen3.8-27B it chose **Q4_K_M (16.8 GB)**, NOT the Q8_0 (28 GB) that was already on disk. Check `total_size_bytes` in the response and the task entries in `~/.lmstudio/.internal/download-jobs-info.json` (fields: `request.url`, `request.savePath`, `download.filename`, `download.totalSizeBytes`).

## savePath nesting quirk

The `savePath` LM Studio chose may nest under an unrelated existing model dir, e.g.:
`~/.lmstudio/models/lmstudio-community/Qwen3.5-35B-A3B-GGUF/lmstudio-community/qwen3.8-27b-gguf/Qwen3.8-27B-Q4_K_M.gguf`
This is a known LM Studio path-management quirk — do NOT "fix" the path; leave the nested dir alone and let LM Studio manage it. Downloads write `downloading_<name>.part` then rename on completion.

## Accelerated workflow (ModelScope fallback)

1. **Start the API download** (above) so the job + hub registration + download tracking all exist. It will crawl at 0.3 MB/s — that's fine, it establishes state.
2. **Verify byte-identity on ModelScope** — same repo, exact same sizes:
```bash
curl -s "https://www.modelscope.cn/api/v1/models/lmstudio-community/Qwen3.8-27B-GGUF/repo/files?Revision=master&Recursive=true" | python3 -m json.tool
# Qwen3.8-27B-Q4_K_M.gguf → 16810714336  (matches LM Studio totalSizeBytes)
# mmproj-Qwen3.8-27B-BF16.gguf → 931145856
```
3. **Download via aria2c from ModelScope** (16 threads, ~10 MB/s):
```bash
mkdir -p /tmp/ms-model-dl && cd /tmp/ms-model-dl
aria2c -x 16 -s 16 --continue=true --user-agent="Mozilla/5.0" \
  -o "Qwen3.8-27B-Q4_K_M.gguf" \
  "https://www.modelscope.cn/models/lmstudio-community/Qwen3.8-27B-GGUF/resolve/master/Qwen3.8-27B-Q4_K_M.gguf"
# mmproj similarly; redirects to cdn-lfs-cn-1.modelscope.cn
```
4. **When complete**: stop the slow LM Studio job (kill LM Studio), delete the `.part` files, copy the ModelScope files to the `savePath` final names, restart LM Studio. The job state + hub registration + on-disk file now agree → model appears in UI. (Session reached step 3; steps 4 completion was pending when the review snapshot was taken — validate the copy-and-restart handoff before relying on it.)

## Time comparison

| Source | Speed | 16.8 GB ETA |
|---|---|---|
| LM Studio proxy (search.lmstudio.ai) | ~0.3 MB/s | ~13 h |
| ModelScope CDN (cdn-lfs-cn-1) | ~10 MB/s | ~26 min |
