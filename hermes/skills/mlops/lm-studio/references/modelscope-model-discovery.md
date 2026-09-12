# ModelScope (魔搭) GGUF Discovery — Direct API, no mirror needed

ModelScope (www.modelscope.cn) is fully reachable from mainland China without DNS tricks, and its REST API is the fastest way to enumerate GGUF quantization files for a model. Verified working 2026-08-15 for Qwen3.8-27B.

## List all files in a model repo (including GGUF variants)

```
GET https://www.modelscope.cn/api/v1/models/{owner}/{repo}/repo/files?Revision=master&Recursive=true
```

- No auth required; plain curl with `User-Agent: Mozilla/5.0` works
- Returns JSON: `data.Files[]` with `Name`, `Size`, `Path`, `Sha256`
- File sizes come straight in `Size` bytes — no need to read READMEs

## Check if a GGUF quantizer repo exists

```
GET https://www.modelscope.cn/api/v1/models/{owner}/{repo}
```

- HTTP 200 with `"Code":200` → exists; `"Code":10010205001` "record not found" → doesn't
- Common quantizer orgs on ModelScope: `unsloth/`, `lmstudio-community/`, `bartowski/` (same as HF)
- Always try both `unsloth/<model>-GGUF` and `lmstudio-community/<model>-GGUF` — the two differ in quantization selection (unsloth has UD variants; lmstudio-community typically ships only Q4_K_M / Q6_K / Q8_0)

## Full text search on ModelScope

The search APIs (`/api/v1/models?search=...`, `/api/v1/dolphin/models?Query=...`) both 404 — do NOT rely on them. Use the direct repo-check endpoint above instead.

## Example — Qwen3.8-27B GGUF variants (verified 2026-08-15)

`unsloth/Qwen3.8-27B-GGUF` (30 files, incl. BF16 split 54.7GB + mmproj):

| Quant | Size | GB10 fit |
|-------|------|----------|
| Q8_0 | 29.05 GB | ✅ (same as Qwen3.6-27B-Q8_0 28.6GB) |
| UD-Q8_K_XL | 31.46 GB | ⚠️ tight |
| UD-Q6_K_XL | 25.92 GB | ✅ |
| Q6_K | 22.88 GB | ✅ |
| UD-Q5_K_XL / Q5_K_M | 20.22 / 19.83 GB | ✅ |
| UD-Q4_K_XL | 17.92 GB | ✅ |
| Q4_K_M | 17.11 GB | ✅ |
| IQ4_NL / IQ4_XS / Q4_0 | 16.34 / 15.71 / 16.06 GB | ✅ |
| UD-IQ3_XXS / Q3_K_M | 11.91 / 13.82 GB | ⚠️ quality loss |
| UD-IQ2_M / UD-Q2_K_XL | 10.32 / 10.68 GB | ❌ too lossy |

`lmstudio-community/Qwen3.8-27B-GGUF` (7 files): Q8_0 29.05GB, Q6_K 22.43GB, Q4_K_M 16.81GB, mmproj-BF16 0.93GB.

**GB10/DGX Spark rule for Qwen3.8-27B:** Q8_0 (29.05GB) fits — the model load is within 1GB of the already-proven Qwen3.6-27B-Q8_0. Check `free -h` first: with ComfyUI running (~36GB), free memory can drop to ~11GB, so unload ComfyUI or close other heavy apps before loading.
