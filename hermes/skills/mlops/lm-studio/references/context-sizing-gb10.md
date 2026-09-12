# Context Sizing & KV Cache Calculation for GB10 Dual-Model

From a live diagnosis session on DGX Spark (GB10, 128GB unified memory) running Qwen3.6-27B + Qwen3.6-35B-A3B simultaneously.

## n_ctx Version Regression

The root cause of "worked before, locks up after update" on GB10:

| Backend Version | Default n_ctx | Multiplies by |
|-----------------|---------------|---------------|
| 2.20.1 / 2.22.0 | **8,192** | — |
| **2.23.0+** | **262,144** | **32×** |

LM Studio's llama.cpp backend 2.23.0+ changed the default context length from 8192 to the model's native max (262144 for Qwen3.6 models). This inflated default can trigger GPU driver timeouts during model loading on unified-memory systems (GB10) even when total memory is adequate.

### Detection

```bash
# Check old and new server logs
grep "n_ctx=" ~/.lmstudio/server-logs/2026-06/*.log | head -5
grep "n_ctx=" ~/.lmstudio/server-logs/2026-07/*.log | head -5
```

Expected finding:
```
Old: LlamaV4::load config: n_parallel=4 n_ctx=8192 kv_unified=true
New: LlamaV4::load config: n_parallel=4 n_ctx=262144 kv_unified=true
```

## Reading GGUF Model Metadata

Use Python's `gguf` reader (shipped with LM Studio backends) to extract exact architecture parameters needed for KV cache calculation:

```python
import gguf

reader = gguf.GGUFReader("model.gguf")
for key, field in reader.fields.items():
    if any(k in key for k in ['block_count','head_count','embedding','expert',
                               'key_length','context_length']):
        # Access actual values from field.parts[3]
        val = field.parts[3].tolist() if hasattr(field.parts[3], 'tolist') else str(field)
        print(f"{key} = {val}")
```

Key parameters to extract:

| Parameter | Purpose |
|-----------|---------|
| `block_count` | Number of transformer layers |
| `head_count_kv` | KV heads for GQA |
| `key_length` | Dimension per KV head (if present; else = embedding / head_count) |
| `expert_count` / `expert_used_count` | MoE topology (not needed for KV calc) |

## KV Cache Memory Formula

**KV cache per token** = `n_layers × n_kv_heads × key_dim × 2 × 2 bytes`
- First `×2`: K and V
- `2 bytes`: fp16 storage (default in llama.cpp)

**Total KV cache for a model** = `n_ctx × KV_per_token`, capped at `prompt_cache` size limit (8192 MiB default).

### Qwen3.6-27B (Dense) Example

| Parameter | Value |
|-----------|-------|
| layers | 64 |
| KV heads | 4 |
| KV head dim | 256 |
| KV per token | 64 × 4 × 256 × 4 = **262,144 bytes ≈ 256 KB** |

| Context | KV Cache (uncapped) | Capped by 8GB prompt cache |
|---------|--------------------|---------------------------|
| 8,192 | 2.1 GB | 2.1 GB |
| 32,768 | 8.4 GB | 8 GB |
| **65,536** | **16.8 GB** | **8 GB** |
| 262,144 | 67 GB | 8 GB |

### Qwen3.6-35B-A3B (MoE) Example

| Parameter | Value |
|-----------|-------|
| layers | 40 |
| KV heads | 2 |
| KV head dim | 256 |
| KV per token | 40 × 2 × 256 × 4 = **81,920 bytes ≈ 80 KB** |

| Context | KV Cache (uncapped) | Capped by 8GB prompt cache |
|---------|--------------------|---------------------------|
| 8,192 | 0.7 GB | 0.7 GB |
| 32,768 | 2.6 GB | 2.6 GB |
| **65,536** | **5.2 GB** | **5.2 GB** |
| 262,144 | 21 GB | 8 GB |

## Dual-Model Feasibility at 64K Context

| Component | 27B Model | 35B-A3B Model |
|-----------|-----------|---------------|
| Weights (Q8_0) | 27 GB | 35 GB |
| KV cache (at 64K) | 8 GB (capped) | 5.2 GB |
| Overhead/buffers | ~9 GB | ~11 GB |
| **Subtotal** | **~44 GB** | **~51 GB** |
| **Combined** | | **~85-95 GB** |

Hardware: 128 GB total (121 GiB usable)
Headroom: **~35-43 GB** ✅ Safe

### Memory Budget Check

```bash
free -h
# Expected: ~121Gi total, target ~80-90Gi in use by LM Studio
```

## Recommended Context Settings by Use Case

| Use Case | Context | Notes |
|----------|---------|-------|
| Agent tasks (requires 64K) | **65,536** | Fits both models with >30GB headroom |
| Chat / repetitive tasks | 32,768 | More headroom, faster prefill |
| Minimal stability | 16,384 | Same as "old defaults" ×2 |
| Legacy / troubleshooting | 8,192 | Match pre-update behavior exactly |

## Qwythos-9B-Claude-Mythos-5-1M (BF16)

Installed at `~/.lmstudio/models/empero-ai/Qwythos-9B-Claude-Mythos-5-1M-GGUF/`. **Only BF16 quantization available** — no Q4/Q8 variants. MTP (Multi-Token Prediction) architecture, 18GB on disk, ~20GB runtime weights.

| Parameter | Value (estimated from GGUF) |
|-----------|--------------------------|
| layers | 48 |
| KV heads | 8 |
| KV head dim | 128 |
| KV per token | 48 × 8 × 128 × 4 = **196,608 bytes ≈ 192 KB** |

| Context | KV Cache (uncapped) | Capped by 8GB prompt cache |
|---------|--------------------|---------------------------|
| 8,192 | 1.6 GB | 1.6 GB |
| 32,768 | 6.3 GB | 6.3 GB |
| 65,536 | 12.6 GB | 8 GB |
| 128,000 | 24.6 GB | 8 GB |

### Dual-Model: Qwen3.6-27B (Q8_0) + Qwythos-9B (BF16)

| Component | Qwen3.6-27B | Qwythos-9B |
|-----------|-------------|------------|
| Weights | 27 GB | 18 GB |
| KV cache (8K ctx) | 2.1 GB | 1.6 GB |
| KV cache (32K ctx) | 8 GB (capped) | 6.3 GB |
| KV cache (128K ctx) | 8 GB (capped) | 8 GB (capped) |
| Overhead/buffers | ~9 GB | ~4 GB |
| **Subtotal** | **~44 GB** | **~26 GB** |

| Context | Combined Memory | Headroom (121GiB) | Verdict |
|---------|----------------|-------------------|---------|
| 8,192 | ~73 GB | ~48 GB | ✅ Safe |
| 32,768 | ~85 GB | ~36 GB | ✅ Safe |
| 65,536 | ~91 GB | ~30 GB | ⚠️ Tight but OK |
| **128,000+** | **~97 GB** | **~24 GB** | ❌ **Danger — swap risk** |

**Previous crash root cause** (nemotron super + qwen3.6-27b): KV cache explosion from long context, NOT model weights. The weights fit; the KV cache at high context length pushed total memory past 121GiB, triggering OOM.

**Rule of thumb**: On GB10 with dual models, keep context ≤ 32K for safety. 64K is acceptable if no other memory-heavy apps run. 128K+ is a crash risk regardless of which models you pair.

## Diagnostic Workflow Summary

1. Check server logs for n_ctx defaults: `grep "n_ctx=" ~/.lmstudio/server-logs/*/*.log`
2. If n_ctx jumped (8192→262144), this is the root cause
3. Read model GGUF metadata for exact KV cache parameters
4. Calculate KV cache at target context using formula above
5. Add weights + KV cache + 20% overhead to estimate total memory
6. If total < 121GiB, manual context reduction fixes the issue
7. If total > 121GiB, reduce context further or use CPU backend
