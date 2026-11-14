# Model Deletion & Speed Measurement

Session-verified workflows for removing models from LM Studio and measuring/diagnosing inference speed on GB10.

## Full Model Deletion (files + UI entry)

Removing a model requires deleting **both** tiers, in this order:

1. **Hub registration first**: `rm -rf ~/.lmstudio/hub/models/<user>/<model>/` — leaving it behind can trigger silent auto-redownload on next startup (see the "hub auto-redownload" pitfall in SKILL.md).
2. **Then the GGUF files**: locate with `find ~/.lmstudio -name "*.gguf"` and delete the model directory, including its mmproj file (~0.9GB each for VLMs).

Caveats:
- Models can be nested in mis-parented directories (e.g. a Qwen3.6-27B folder inside `Qwen3.5-35B-A3B-GGUF/lmstudio-community/`) — locate by filename, not expected path.
- Don't delete the currently loaded/serving model; unload it first via `/api/v1/models/unload` or restart LM Studio afterwards.
- Verify with a **scoped** grep: `grep -rl "<model-name>" ~/.lmstudio/hub/ 2>/dev/null` should return nothing. Do NOT grep the whole `~/.lmstudio` tree — it's slow (times out past ~60s) and logs add noise.

Worked example (2026-08): deleted Qwen3.6-27B-Q8_0 (28G incl. mmproj, nested under the Qwen3.5 directory) + its hub registration `~/.lmstudio/hub/models/qwen/qwen3.6-27b/`. Disk freed 276G → 249G; scoped grep confirmed no residue.

## Measuring Inference Speed (TTFT + tok/s)

`scripts/measure-speed.py` streams a test prompt through `/v1/chat/completions` and reports time-to-first-token plus generation speed:

```bash
python3 scripts/measure-speed.py                          # first model from /v1/models
python3 scripts/measure-speed.py --model qwen/qwen3.8-27b@q8_0 --max-tokens 400
```

Speed is a chunk-based estimate (LM Studio emits ~1 chunk per token). Reference numbers on GB10 (DGX Spark, CUDA backend): Qwen3.8-27B Q8_0 ≈ TTFT 2.3s / ~14.5 tok/s at short context; MoE A3B models run far faster (~60+ tok/s). Long system prompts + conversation history inflate TTFT — treat measured numbers as a lower bound for real conversations.

## Diagnosing Slow Inference (separate prefill from thinking overhead)

When the user reports slow local inference (especially "image inference is slow"), do NOT assume the vision encoder or GPU is at fault — measure first. On GB10 with Qwen3.x models the dominant hidden cost is **thinking tokens**: the chat template defaults to `reasoning_effort=xhigh`, so every request generates ~85–98 reasoning tokens (~8s at 27B Q8_0 speed) before any visible content, for text and images alike.

Procedure (all via `/v1/chat/completions`):

1. **Baseline text**: short prompt, non-streaming → tok/s = `usage.completion_tokens / elapsed`. ~11–14 tok/s is the GB10 bandwidth ceiling for 27B Q8_0; MoE A3B runs 60+. If baseline is already at the ceiling, generation speed cannot be improved by any request-level knob.
2. **Pure prefill cost**: same request with `"max_tokens": 1` — elapsed ≈ prompt processing (vision encoding included). Compare an image message against a text-only message of similar `prompt_tokens`: on Qwen3.8-27B a 1080p JPEG (~2100 tokens) added only ~1s over equivalent-length text. Vision prefill is rarely the bottleneck; thinking overhead is.
3. **Smoking gun**: check `usage.completion_tokens_details.reasoning_tokens` in non-streaming responses — if it's a large fixed number on every request, the model thinks before answering regardless of content or prompt wording.
4. **Check template defaults**: `strings <model>.gguf | grep -c enable_thinking`, then look for `reasoning_effort|default(...)` lines to see supported levels (Qwen3.8-27B: xhigh default / medium / low). The template may support lower efforts even when the server can't reach them.

Verified on LM Studio v0.4.18 — **none of the API-level reasoning controls reach the template** (A/B tested, 2 runs each; `reasoning_tokens` stayed ~75–98 in every condition):
- `chat_template_kwargs: {"enable_thinking": false}` — ignored
- `/no_think` in user text — ignored (still thinks)
- top-level `"reasoning_effort": "low" | "none"` — ignored

So the only levers are model choice (MoE A3B makes thinking cheap), quantization (Q4_K_M ≈ 2× speed, halves thinking time), or running llama-server directly where template variables can be passed. Re-verify after any LM Studio upgrade before repeating these dead ends.

**Measurement discipline**: single-run TTFT comparisons are noisy (7–14s variance observed across identical conditions) — run each condition ≥2 times and compare `reasoning_tokens` from usage, not wall-clock alone.
