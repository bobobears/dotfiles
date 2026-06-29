# Model Card URL Patterns

Known locations for official model cards and research information for major LLM families.

## Meta / Llama

| Model | URL |
|-------|-----|
| Llama 3.3 70B | `https://raw.githubusercontent.com/meta-llama/llama-models/refs/heads/main/models/llama3_3/MODEL_CARD.md` |
| Llama 3.1 | `https://raw.githubusercontent.com/meta-llama/llama-models/refs/heads/main/models/llama3_1/MODEL_CARD.md` |
| Llama 3 | `https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3/MODEL_CARD.md` |

Structure: `<org>/llama-models/models/<model_name>/MODEL_CARD.md`

HF mirror (for gated access): `https://hf-mirror.com/api/models/meta-llama/<ModelName>` — returns cardData even when README is gated.

Community quant repos that mirror official data:
- `hf-mirror.com/bartowski/<ModelName>-GGUF/raw/main/README.md`
- `hf-mirror.com/unsloth/<ModelName>-GGUF/raw/main/README.md`
- `hf-mirror.com/hugging-quants/<ModelName>-AWQ-INT4/raw/main/README.md`

## Qwen / Alibaba

Official models on HF: `https://hf-mirror.com/Qwen/`
Blog: `qwen.ai/blog` (qwenlm.github.io redirects to qwen.readthedocs.io which is tech docs, not a blog)
Technical reports: arxiv

## Alibaba (DashScope API models)

Qwen Max, Qwen Plus, Qwen Turbo are **API-only** — no weights released. Their data comes from Qwen's blog/tech report, not HF model cards.

## General pattern for HF gated repos

```
# Get metadata (always works)
curl -sL "https://hf-mirror.com/api/models/<org>/<model>"

# Try README (may be gated)
curl -sL "https://hf-mirror.com/<org>/<model>/raw/main/README.md"

# Search
curl -sL "https://hf-mirror.com/api/models?search=<term>"
curl -sL "https://hf-mirror.com/models?search=<term>&sort=downloads"
```
