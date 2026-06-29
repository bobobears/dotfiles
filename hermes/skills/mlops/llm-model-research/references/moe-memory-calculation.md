# MoE Model Memory Calculation

## The #1 Rule: TOTAL params matter for memory, not active params

MoE (Mixture of Experts) models have two parameter counts:
- **Total params** — all parameters stored in memory (determines GGUF file size and VRAM)
- **Active params** — params activated per forward pass (determines inference speed, NOT memory)

For memory estimation, **treat a MoE model as if it were a dense model of the total-param size.**

## Quick Memory Formula

```
GGUF file size ≈ Total_Params × Bits_per_Weight / 8  (GB at Q4 = total_B × 0.5)
RAM/VRAM at load ≈ GGUF_file_size × 1.08  (8% overhead for KV cache + buffers)

For MoE with large expert count:
RAM/VRAM ≈ GGUF_file_size × 1.12  (12-15% overhead — more experts = more routing metadata)
```

## Quantization Multipliers

| Quant | Bits/Weight | Multiplier (GB per 1B params) |
|-------|-------------|-------------------------------|
| Q2_K  | 2.5         | 0.31 GB/B                    |
| Q3_K_M| 3.5         | 0.44 GB/B                    |
| Q4_K_M| 4.5         | 0.56 GB/B                    |
| Q5_K_M| 5.5         | 0.69 GB/B                    |
| Q6_K  | 6.5         | 0.81 GB/B                    |
| Q8_0  | 8.5         | 1.06 GB/B                    |
| BF16  | 16          | 2.00 GB/B                    |
| FP32  | 32          | 4.00 GB/B                    |

## Worked Examples from This Session

| Model | Total Params | Active | Quant | File Size | Loaded RAM |
|-------|-------------|--------|-------|-----------|------------|
| Qwen3.6-35B-A3B | 35B | 3B | Q4_K_M | ~20 GB | ~23 GB |
| Qwen3.6-35B-A3B | 35B | 3B | Q8_0 | ~37 GB | ~40 GB |
| Qwen3-Coder-30B-A3B | 30.5B | 3.3B | Q4_K_M | ~17 GB | ~19 GB |
| Nemotron-3-Nano-30B-A3B | 30B | 3.5B | Q4_K_M | ~17 GB | ~20 GB |
| Gemma4-26B-A4B | 25.2B | 4B | Q4_K_M | ~15 GB | ~18 GB |
| Nemotron-3-Super-120B-A12B | 120B | 12B | Q4_K_M | ~86 GB | ~92 GB |
| Qwen3.5-27B (dense) | 27B | 27B | Q4_K_M | ~15 GB | ~17 GB |

## The Common Mistake

```
WRONG: Nemotron-120B Q4_K_M = 12B_active × 4.5 bits / 8 = 6.75 GB
CORRECT: Nemotron-120B Q4_K_M = 120B_total × 4.5 bits / 8 = 67.5 GB (file) → ~92 GB (loaded)

The 512 experts are ALL stored in memory, even though only 22 are active per token.
```

## Why MoE Uses More Memory Per Param

1. **Experts are separate FFN matrices** — 128 or 256 sets of expert weights, each 2-4 GB at Q4
2. **Router network** — additional parameters for the gating/routing mechanism
3. **Shared experts** — 1-2 non-routed experts that fire on every token
4. **Multi-split GGUF** — MoE models often ship as 3-10 shard files; sharding adds minimal overhead but is worth noting

## Practical Rule of Thumb

To check if a MoE model fits in your VRAM/RAM:

```
Available_RAM ≥ Total_Params_B × 0.56 × 1.12  (for Q4_K_M on a unified memory system)
```

For DGX Spark (128GB unified, ~122GB usable):
- Max Q4_K_M model: ~195B total params (120B comfortable)
- Max Q8_0 model: ~103B total params (35B comfortable)
