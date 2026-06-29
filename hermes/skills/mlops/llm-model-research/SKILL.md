---
name: llm-model-research
description: "Research, evaluate, and compare open-source LLMs by extracting data from HuggingFace mirrors, official model cards, and community quantized repos. Covers: model card extraction, benchmark table scraping, multi-source cross-referencing, and evaluation report generation."
version: 1.0.0
author: Agent-created
license: MIT
tags: [llm, model-research, evaluation, benchmark, huggingface, model-discovery, model-comparison]
platforms: [linux, macos]
---

# LLM Model Research & Evaluation

Use this skill when the user asks to evaluate, compare, or research an open-source LLM — including questions like "how is model X", "compare model A vs B", "what are the benchmarks for C", "what versions of D exist", or "does model E exist".

## When to use

- User asks for model evaluation, comparison, or capability assessment
- User asks if a model exists or what version is current
- User wants benchmark numbers, architecture details, or release info
- User wants to know how a model compares to alternatives

## Workflow

### Step 0: Identify the target size tier

Before searching, establish the model size class you're comparing:

- **Small MoE (16-35B total / 2-4B active):** Qwen3.6-35B-A3B, Qwen3-Coder-30B-A3B, Nemotron-3-Nano-30B-A3B, Gemma4-26B-A4B, DeepSeek-Coder-V2-Lite
- **Mid Dense (70-90B):** Llama 3.3 70B, Qwen3.5-72B, DeepSeek-V2-Lite (16B MoE — note it's smaller than the name suggests)
- **Large MoE (120-240B total / 12-22B active):** Nemotron-3-Super-120B-A12B, DeepSeek-V2 (236B total), Mixtral 8x22B
- **Flagship (400B+):** Llama 3.1 405B, DeepSeek-V3 (671B MoE)

When the user says "同量级", search within the same tier. MoE models are deceptive — their **total** params determine VRAM/GGUF size, not the active params. A "30B A3B" model's GGUF is sized like a 30B dense model, even though it runs at ~3B-active speed.

### Step 1: Determine the search strategy

Three main data sources, tried in this order:

**Source A: Official model card** (highest authority)
- Meta/other vendors often host model cards on GitHub: `https://raw.githubusercontent.com/<org>/<repo>/refs/heads/main/models/<model>/MODEL_CARD.md`
- Example: `https://raw.githubusercontent.com/meta-llama/llama-models/refs/heads/main/models/llama3_3/MODEL_CARD.md`
- The model card contains the official benchmark table, architecture details, training data, and safety info
- Use `curl -sL` with a 15-20s timeout

**Source B: HuggingFace (via China mirror)**
- Primary: `hf-mirror.com` (works from mainland China)
- Search API: `curl -sL "https://hf-mirror.com/api/models?search=<query>"` — returns JSON with model ID, likes, downloads
- Individual model page: `curl -sL "https://hf-mirror.com/api/models/<org>/<model>"` — returns detailed metadata
- README (gated models return 403): `curl -sL "https://hf-mirror.com/<org>/<model>/raw/main/README.md"`
- Community quant repos (unsloth, bartowski, hugging-quants) often mirror official README content even when the official repo is gated
- Chinese network: HF raw content works via hf-mirror.com but raw.githubusercontent.com may need ghproxy

**Source C: Community download pages**
- Community quantized versions (e.g. `unsloth/<ModelName>-GGUF`, `bartowski/<ModelName>-GGUF`, `hugging-quants/<ModelName>-AWQ-INT4`) often carry the original benchmark table in their README
- Check these when the official repo is gated (403 on README)

### Step 2: Extract benchmark data

The typical model card benchmark table looks like:

| Category | Benchmark | Score |
|----------|-----------|-------|
| General | MMLU | XX.X |
| Code | HumanEval | XX.X |
| Math | MATH | XX.X |
| Reasoning | GPQA | XX.X |
| Multilingual | MGSM | XX.X |

Key patterns to look for:
- Compare against predecessor models (same-family baselines)
- Note which benchmarks the model exceeds larger models on
- Pay attention to multilingual benchmarks for Chinese-capable models

### Step 3: Cross-reference model lineage

- Check `base_model` field in cardData to understand architecture lineage
- Compare with the current latest version in the same family
- Check release dates to understand recency
- Verify model existence by checking multiple sources before concluding a model version doesn't exist

### Step 4: Structure the evaluation report

Structure responses with these sections:

```
# <Model Name> — Evaluation

## Basic Info
| Key | Value |
|-----|-------|

## Official Benchmarks
| Category | Benchmark | Score | vs Predecessor | vs Larger Model |

## Key Highlights
- Bullet points of standout capabilities

## Limitations
- Key limitations and constraints

## Comparison to Alternatives (when relevant)
| Dimension | This Model | Competitor |

## Summary & Use Cases
- Best for...
- Avoid for...
```

### Step 5: Handle gated/restricted repos

When the official HF repo is gated (returns "Access restricted" on README):
1. Try the `api/models/<org>/<model>` endpoint for metadata (tags, cardData, base_model)
2. Check community quantized repos (unsloth, bartowski, hugging-quants, mradermacher, TheBloke) which often mirror the official README
3. For Meta models specifically, try the official GitHub model cards repository
4. The HF API endpoint still returns cardData (language, base_model, tags) even for gated repos

## Pitfalls

- **MoE memory: TOTAL params, not active params, determine GGUF file size and VRAM** — This is the #1 mistake. A "35B-A3B" model is a 35B model for memory purposes. A 120B-A12B model requires ~92GB at Q4_K_M (120B × 4.5 bits), not 12B × 4.5 bits. Always use **total** params × quantization bits for memory estimation — see `references/moe-memory-calculation.md` for the exact formula.
- **hf-mirror.com is for API and page access only** — model downloads need the full mirror URL
- **Gated repos return 403** on `raw/main/README.md` — don't keep retrying, switch to alternative sources
- **hf-mirror.com/meta-llama page doesn't show Llama 3.3** — Meta doesn't list it on the org page, use direct README URL or community repos instead
- **Google/Bing search timing out from China** — accept this and rely on hf-mirror.com + GitHub raw content
- **Model doesn't exist** — confirm negative answer by checking: HF API search, HF org page, GitHub org, official blog. A single community upload with the name doesn't prove official existence
- **Knowledge cutoff matters** — check the model card's stated knowledge cutoff date; models with old cutoffs (e.g. Dec 2023) may lack recent information despite being newly released
- **Only 70B in the family** — note when a model only comes in one size (unlike families with 8B/70B/405B tiers)
- **Official supported languages ≠ actual capability** — report what the model card states, but note Chinese capability may be present even if not officially supported (e.g. Llama 3.3 doesn't list Chinese but many users report it works)

## References

See `references/model-card-sources.md` for known model card URL patterns.
See `references/hf-mirror-queries.md` for common HF API query patterns.

## Related skills

- `huggingface-hub` — for the `hf` CLI when the user wants to download or upload models, not just research them
- `llama-cpp` — for GGUF inference and quant selection after a model is chosen
- `serving-llms-vllm` — for production serving after a model is chosen
