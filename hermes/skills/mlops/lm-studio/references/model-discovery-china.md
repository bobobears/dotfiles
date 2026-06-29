# Model Discovery from China Network

## HuggingFace via hf-mirror.com

When HuggingFace is blocked by DNS/GFW, use `hf-mirror.com`:

```bash
# List models by name
curl -sL "https://hf-mirror.com/api/models?search=nvidia+nemotron&sort=downloads&direction=-1&limit=10"

# Get file sizes from a quantizer's README
curl -sL "https://hf-mirror.com/bartowski/nvidia_Nemotron-3-Super-120B-A12B-GGUF/raw/main/README.md"

# Download with mirror (small files ≤5GB)
export HF_ENDPOINT=https://hf-mirror.com
hf download <user>/<model> --include "*.gguf" --local-dir ./

# For large files >5GB, use aria2c (multi-threaded, resumable)
# See references/model-download-china.md for full workflow
aria2c -x 4 -s 4 --continue=true \
  --header="User-Agent: huggingface-hub/1.21.0" \
  -o "<filename.gguf>" \
  "https://hf-mirror.com/<user>/<model>/resolve/main/<filename.gguf>"
```

## Nemotron-3-Super GGUF Quantizers (Popularity Order)

From hf-mirror.com API search (`search=nemotron+3+super+GGUF`, sorted by downloads):

| Quantizer | Downloads | Notes |
|-----------|-----------|-------|
| `unsloth/NVIDIA-Nemotron-3-Super-120B-A12B-GGUF` | ~11K | Many quantization levels including UD variants |
| `lmstudio-community/NVIDIA-Nemotron-3-Super-120B-A12B-GGUF` | ~9.6K | LM Studio optimized, Q4_K_M / Q6_K / Q8_0 |
| `bartowski/nvidia_Nemotron-3-Super-120B-A12B-GGUF` | ~6K | Full range from IQ1_S to Q8_0, detailed README with sizes |

## File Size Reference (bartowski — Nemotron-3-Super-120B-A12B)

| Quant | Size | Split | GB10 (80GB) |
|-------|------|-------|-------------|
| Q8_0 | 128.47 GB | 4 files | ❌ Too large |
| Q6_K | 113.56 GB | 4 files | ❌ Too large |
| Q5_K_M | 96.60 GB | 4 files | ❌ Too large |
| Q5_K_S | 87.56 GB | 4 files | ❌ Too large |
| Q4_K_M | 86.98 GB | 3 files | ❌ OOM on CUDA |
| Q4_0 | 70.99 GB | 3 files | ⚠️ Very tight |
| IQ4_XS | 67.20 GB | 3 files | ⚠️ Tight |
| **Q3_K_M** | **64.65 GB** | 3 files | **✅ Best fit** |
| IQ3_XS | 64.54 GB | 3 files | ✅ Good fit |
| Q3_K_S | 61.13 GB | 3 files | ✅ OK, lower quality |
| Q2_K | 54.82 GB | 2 files | ✅ Low quality |

**Rule of thumb:** On DGX Spark (80GB unified), need ≥15GB headroom for CUDA13 backend. So models ≥65GB are risky with CUDA, models ≤65GB are safe.
