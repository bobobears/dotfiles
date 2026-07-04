# GGUF Header Metadata Reading

Use the Python `gguf` library (shipped with llama.cpp / LM Studio backends) to extract model architecture parameters directly from a `.gguf` file's header. This works on any GGUF file regardless of the inference engine.

## When to Use

- Determine a model's **native context length** before loading
- Calculate **KV cache memory** requirements for a given context setting
- Verify **MoE topology** (expert count, active experts)
- Compare **architecture differences** between model families
- Get **head counts, layer counts, and embedding dimensions** for memory planning

## Basic Usage

```python
import gguf

reader = gguf.GGUFReader("path/to/model.gguf")

for key, field in reader.fields.items():
    # Skip internal/tokenizer fields
    if any(k in key for k in ['tokenizer', '.chat_', 'bos_', 'eos_', 'GGUF.']):
        continue
    # Access actual value from the 4th part (index 3)
    val_data = field.parts[3]
    if hasattr(val_data, 'tolist'):
        value = val_data.tolist()
    elif hasattr(val_data, '__iter__'):
        value = [x.item() if hasattr(x, 'item') else x for x in val_data[:10]]
    else:
        value = str(val_data)[:100]
    print(f"{key} ({field.types[0].name}) = {value}")
```

## Key Parameters to Extract

| GGUF Key | Type | Purpose |
|----------|------|---------|
| `general.architecture` | STRING | `llama`, `qwen35`, `qwen35moe`, `nemotron`, etc. |
| `*.block_count` | UINT32 | Number of transformer layers |
| `*.context_length` | UINT32 | Model's native max context (may be huge: 8192–262144+) |
| `*.embedding_length` | UINT32 | Hidden dimension size |
| `*.attention.head_count` | UINT32 | Total query heads (Q heads) |
| `*.attention.head_count_kv` | UINT32 | KV heads for grouped-query attention (GQA) |
| `*.attention.key_length` | UINT32 | KV head dimension (may differ from head_count_kv ratio) |
| `*.attention.value_length` | UINT32 | Value head dimension |
| `*.expert_count` | UINT32 | Total MoE experts (present only in MoE arch) |
| `*.expert_used_count` | UINT32 | Active experts per forward pass |
| `*expert_feed_forward_length` | UINT32 | MoE expert FFN dimension |
| `*expert_shared_feed_forward_length` | UINT32 | Shared expert FFN dimension |
| `*.feed_forward_length` | UINT32 | FFN hidden dimension (dense models only) |
| `*.rope.dimension_count` | UINT32 | RoPE dimension (for NTK-aware scaling) |
| `general.file_type` | UINT32 | Quantization format code (1=Q4_0, 2=Q4_1, 7=Q8_0, 10=Q6_K) |
| `general.quantization_version` | UINT32 | GGUF quant version (usually 2) |

## Architecture Prefix Convention

The model architecture prefix (e.g. `qwen35`, `qwen35moe`, `llama`) is set by `general.architecture`. All model-specific keys use this prefix (e.g. `qwen35.block_count` for Qwen3.6-27B, `qwen35moe.block_count` for Qwen3.6-35B-A3B).

## KV Cache Memory Calculation

Relies on parameters extracted above:

```
KV_cache_per_token = n_layers × n_kv_heads × key_dim × 2 (K+V) × 2 bytes (fp16)
```

where `key_dim` = `attention.key_length` if present, else `embedding_length / head_count`.

Total KV cache at context N = `N × KV_cache_per_token`, typically capped by llama.cpp's `--cache-type-k/v` and prompt cache size limits.

## Example: Qwen3.6 Models

Extracted from live DGX Spark (GB10) session:

**Qwen3.6-27B (Dense, Q8_0):**
- Architecture: `qwen35`, 64 layers, embedding=5120
- KV heads: 4, KV head dim: 256, KV/token: **256 KB**
- Native context: 262,144

**Qwen3.6-35B-A3B (MoE, Q8_0):**
- Architecture: `qwen35moe`, 40 layers, embedding=2048
- KV heads: 2, KV head dim: 256, KV/token: **80 KB**
- MoE: 256 experts, 8 active, expert_ffn=512
- Native context: 262,144

## Pitfalls

- **GGUF v2 vs v3 field layout differs slightly** in how key lengths and value types are encoded. Always use the `gguf` Python library rather than implementing your own binary parser — it handles version differences and endianness correctly.
- **The `head_count_kv` may not equal `head_count / kv_groups`** for models with hybrid attention+SSM architectures. Always read `key_length` from the file when available rather than computing it.
- **STRING values** (architecture, model name) appear as arrays of bytes in `.parts[3]`. Convert with `.tolist()` and compare to the raw bytes; the library handles the decoding.
- **DO NOT assume architecture keys match between model families.** `qwen35.*` keys differ from `qwen35moe.*` keys (the latter uses `expert_count` not `block_count` as the primary topology indicator).
