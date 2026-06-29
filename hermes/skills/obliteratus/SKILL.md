---
name: obliteratus
description: "OBLITERATUS: abliterate LLM refusals (diff-in-means)."
version: 2.0.0
author: Hermes Agent
license: MIT
dependencies: [obliteratus, torch, transformers, bitsandbytes, accelerate, safetensors]
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Abliteration, Uncensoring, Refusal-Removal, LLM, Weight-Projection, SVD, Mechanistic-Interpretability, HuggingFace, Model-Surgery]
    related_skills: [vllm, gguf, huggingface-tokenizers]
---

# OBLITERATUS Skill

Abliterate LLMs to remove refusal behavior using diff-in-means projection.

## What's inside

9 CLI methods, 28 analysis modules, 116 model presets, tournament evaluation.

## Quick Start

```bash
# Install
pip install obliteratus

# Abliterate a model
obliteratus abliterate --model Qwen/Qwen2-7B-Instruct --device cuda

# Interactive chat with abliterated model
obliteratus chat --model ./abliterated-model
```

## Key Concepts

- **Diff-in-Means**: Find refusal direction in activation space by comparing "refusal" prompts vs "compliant" prompts
- **Abliteration**: Project out the refusal direction from each layer's weights
- **Preserves capability**: Only removes the refusal mechanism, not the model's knowledge

## Methods

| Method | Description | Speed |
|--------|-------------|-------|
| `abliterate` | Standard diff-in-means | Fast |
| `turbo` | Optimized version | Fastest |
| `selective` | Layer-by-layer selection | Medium |
| `tournament` | Evaluate multiple methods | Slow |
