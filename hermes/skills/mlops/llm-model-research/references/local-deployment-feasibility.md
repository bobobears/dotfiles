# Local Deployment Feasibility — Worked Example: DeepSeek-V4-Flash

Session date: 2026-08-05. All sizes measured live via hf-mirror.com tree API.

## Machine being evaluated

NVIDIA DGX Spark (GB10, ARM64, Blackwell), **128GB unified memory** (121GiB per `free -h`).
- nvidia-smi shows GB10 with "Memory-Usage: Not Supported" — GPU shares system RAM, no dedicated VRAM counter
- CUDA 13.0, Driver 580.142
- Lesson: always read `free -h`, not nvidia-smi, for unified-memory machines

## The question

"DeepSeek V4 Flash 权重多大？本机可以本地部署吗？"

## Architecture (from config.json — not gated)

```
architectures: DeepseekV4ForCausalLM
model_type: deepseek_v4
hidden_size: 4096, num_hidden_layers: 43
num_attention_heads: 64, num_key_value_heads: 1 (MLA)
vocab_size: 129280
n_routed_experts: 256, num_experts_per_tok: 6, n_shared_experts: 1
moe_intermediate_size: 2048
quantization_config: fp8 (e4m3, weight_block_size [128,128])
```

≈ **160B total params** (MoE). Official weights ship FP8 already.

## Weight size ladder (measured)

| Version | Size | Notes |
|---------|------|-------|
| Official FP8 (DeepSeek-V4-Flash, 2026-04-22 preview) | 159.6 GB | 46 shards |
| Official FP8 (DeepSeek-V4-Flash-DSpark, 2026-06-27) | 166.9 GB | main model + speculative-decoding draft module |
| Official 0731 GA (2026-07-31, what the API serves) | ~160 GB | same structure as DSpark |
| nvidia/DeepSeek-V4-Flash-NVFP4 | 168.3 GB | NOT half-size; NVFP4 label ≠ smaller file here |
| unsloth GGUF Q8_K_XL (near-lossless) | 161.9 GB | "only 7GB bigger than Q4" per unsloth |
| unsloth GGUF Q4_K_XL | 155.1 GB | quality/size sweet spot |
| unsloth GGUF IQ4_XS / IQ4_NL | 136.7 GB | |
| unsloth GGUF Q3_K_XL / Q3_K_M | 128.2 / 128.1 GB | right at the 128GB line — no room for KV cache |
| unsloth GGUF IQ3_S | 116.1 GB | borderline usable on 128GB |
| unsloth GGUF IQ2_M / IQ2_XXS | 90.9 GB | viable on 128GB, quality loss visible |
| unsloth GGUF IQ1_S | 82.5 GB | smallest full quant, big quality loss |
| unsloth `dspark/` draft model Q8_0 | 10.9 GB | speculative-decoding draft only, NOT the main model |
| unsloth `dspark/` draft model BF16 | 11.3 GB | |

## Verdict for 128GB machine

- Full precision (FP8/Q4/Q8, 155-167GB) → **does not fit**
- Usable quants on 128GB: IQ3_S (116GB) marginal, IQ2_M (91GB) workable
- Quality loss at IQ2/IQ3 makes local deployment unattractive for a production main model
- True full-precision local run needs 192GB+ RAM or dual-node inference
- The official DSpark variant is a main-model + 10-11GB draft-model combo for speculative decoding, not a shrunken single file

## Recommended decision pattern for this class of question

1. `free -h` to get real RAM (not assumptions from memory)
2. Tree API → total weight size per version (official + quant ladder)
3. Compare weight vs RAM with ~25% headroom for KV cache/runtime
4. If too big: report the gap + smallest viable quant + what hardware WOULD fit
5. Weigh quant quality loss against the use case (production main model vs experiment)

## Query recipes (hf-mirror, no API key)

```bash
# Search any model name across the hub
curl -s "https://hf-mirror.com/api/models?search=<name>&limit=30"

# Latest models from an org, newest first (use before claiming a version is missing)
curl -s "https://hf-mirror.com/api/models?author=<org>&sort=createdAt&direction=-1&limit=20"

# Weight files + sizes for one repo
curl -s "https://hf-mirror.com/api/models/<org>/<model>/tree/main?recursive=true"

# config.json (architecture, never gated)
curl -sL "https://hf-mirror.com/<org>/<model>/resolve/main/config.json"

# Aggregating GGUF shards by quant level
curl -s "https://hf-mirror.com/api/models/<org>/<model>/tree/main?recursive=true" | python3 -c "
import json,sys
from collections import defaultdict
data=json.load(sys.stdin)
tot=defaultdict(float)
for f in data:
    p=f.get('path','')
    if p.endswith('.gguf') and '/' in p:
        tot[p.split('/')[0]] += f.get('size',0)
for q in sorted(tot, key=tot.get):
    print(f'{q}: {tot[q]/1e9:.1f} GB')"
```
