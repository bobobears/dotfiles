# Model Combo Recommendations for Unified Memory Systems

When a user asks "what models should I run on my machine?", the recommendation depends on their hardware specs first. This reference captures the methodology and data points for the DGX Spark / GB10 / 128GB class.

## Key Questions to Answer First

1. **Total unified memory** — 16GB, 32GB, 64GB, 128GB? (DGX Spark = 128GB, ~121GB usable)
2. **CUDA or CPU backend?** — Check `~/.lmstudio/.internal/backend-preferences-v1.json` and `internal-engine-index.json` GPU survey
3. **Already downloaded models?** — Check `~/.lmstudio/models/` for .gguf files
4. **Disk space** — `df -h /` (DGX Spark has ~3.4TB free out of the box)
5. **Use case** — Coding/Agent? Chat/Reasoning? Chinese vs English? RAG?
6. **Current loaded model** — Check `model-data.json` `lastLoadedTimestamp` or `/v1/models` API

## Classification by Hardware Class

### Class A: 128GB Unified Memory (DGX Spark / GB10 Grace Blackwell)

**MoE models are ideal** — the unified memory means all experts stay in memory, no swapping.

| Tier | Model | Quant | Disk | ~Memory | Use | Notes |
|:----:|:------|:-----:|:----:|:-------:|:----|:------|
| 🥇 | Qwen3.6-35B-A3B | Q8_0 | 34G | ~12G | **Daily driver**: Agent, Coding, Chinese, MCP | Fastest option. 3B active params. Apache-2.0. |
| 🥇 | Nemotron-3-Super-120B-A12B | Q4_K_M | 86G | ~30G | **Heavy reasoning**: complex logic, long docs | 22 active experts. Use CUDA13 for 20 tok/s. |
| 🥈 | Llama 3.3 70B | Q4_K_M | ~40G | ~42G | **English/instruction-following**: IFEval 92.1 | Dense model, bigger memory footprint than MoE. |
| 🥉 | Nomic Embed Text v1.5 | Q4_K_M | 27M | <1G | **Embedding / RAG** | Bundled with LM Studio. Always keep. |

**Key insight**: The user only loads ONE model at a time (LM Studio `unloadPreviousModelOnSelect: true`). Each of the above fits comfortably alone in 128GB with 80-100GB headroom.

**Qwen3.6 Q8_0 vs Q4_K_M tradeoff**:
- Q8_0 (34GB): near-lossless precision, ~3B active params so still very fast
- Q4_K_M (19GB estimated): smaller, but the 3B active params mean quality loss is minimal on MoE
- Recommendation: prefer Q8_0 since the disk is abundant and unified memory handles it easily

### Class B: 32-64GB (Typical Mac/PC)

Focus on smaller MoE models and Q4_K_M quantizations:
- Qwen3.6-35B-A3B Q4_K_M (19GB) — fits well
- Llama 3.1 8B Q4_K_M (~5GB) + an embedding model
- Smaller MoE models: Qwen2.5-7B variants

### Class C: 16GB (Consumer Laptops)

- Mistral 7B / Qwen2.5 7B Q4_K_M (~4GB)
- Phi-3 / Phi-4 mini variants
- Or use cloud models exclusively

## Qwen3.6 vs Qwen3.5 vs Llama 3.3 — Quick Reference for Recommendations

| Criterion | Pick Qwen3.6 | Pick Llama 3.3 |
|:----------|:-------------|:---------------|
| Chinese tasks | ✅ Native | ❌ Not supported |
| Agent/Coding/SWE-bench | ✅ Far superior | ❌ Standard only |
| English instruction-following | Good | ✅ IFEval 92.1 (best in class) |
| Multi-language (8 lang) | ❌ CN/EN focus | ✅ Officially supports 8 languages |
| Open license | ✅ Apache-2.0 | ❌ Meta custom license |
| Replaces 405B class | ✅ Close for code/agent | ✅ Surpasses on IFEval/GPQA/MATH |
| Multimodal (vision) | ✅ 262K context | ❌ Text-only |

## Verification After Recommendation

```bash
# Check existing models with sizes
find ~/.lmstudio/models -name "*.gguf" -type f -exec ls -lh {} \;

# Check current LM Studio backend
cat ~/.lmstudio/.internal/backend-preferences-v1.json

# Check what's downloading (active transfers)
cat ~/.lmstudio/.internal/single-downloads-info.json | python3 -c "
import sys, json
d = json.load(sys.stdin)
for key, val in d.get('downloadsMap', {}).get('map', [[], []])[1].items():
    stype = val['status']['type']
    total = val.get('totalSizeBytes', 0)
    done = val.get('downloadedSizeBytes', 0)
    print(f\"{val['filename']}: {stype} {done/total*100:.0f}%\" if total else f\"{val['filename']}: {stype}\")
"

# Check disk space
df -h /
