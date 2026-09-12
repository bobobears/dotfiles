---
name: lm-studio
description: "Configure, optimize, and troubleshoot LM Studio local inference server — memory tuning, crash/deadlock diagnosis, unified-memory systems (NVIDIA GB10/Project DIGITS), context sizing, and Hermes integration."
version: 1.10.0
author: Agent
platforms: [linux, macos]
tags: [lm-studio, inference, serving, gguf, local-llm, openai-api]
---

# LM Studio Local Inference

Guide for running LM Studio as a local inference server, diagnosing crashes/freezes, installing/upgrading, and optimizing memory on unified-memory systems like NVIDIA GB10 (Project DIGITS, Grace Blackwell).

## Architecture

LM Studio is an Electron app that wraps:
- **llama.cpp** (`llama-server`) — the actual inference engine
- **HTTP API** on port 1234 (configurable) — OpenAI-compatible endpoints (`/v1/chat/completions`, `/v1/models`, etc.)
- **JIT model loading** — loads/unloads models on demand (can be disabled)

Two API namespaces:
- `/v1/...` — OpenAI-compatible (used by Hermes agents)
- `/api/v1/...` — LM Studio native (model load, download management)

## Installation & Upgrade (Linux AppImage)

LM Studio is distributed as a self-contained **AppImage** on Linux. Configuration and model data live in `~/.lmstudio/` and survive AppImage replacements. On Chinese-locale systems, the download directory is `~/下载/`.

### Install

```bash
# Move the downloaded AppImage to home directory
mv ~/下载/LM-Studio-*.AppImage ~/LM-Studio.AppImage
chmod +x ~/LM-Studio.AppImage

# Launch (requires --no-sandbox on most systems)
~/LM-Studio.AppImage --no-sandbox
```

### Upgrade (overwrite existing)

> ⚠️ **Step 0（用户约定，必做）：升级前先切 Hermes 模型到 DeepSeek。**
> 升级期间本地 LM Studio 会重启、模型不可用——若当前会话正跑在本地 Qwen 上，kill/替换 AppImage 会让进行中的请求中断。所以**开始任何升级动作前**先把主模型切到云端 DeepSeek：
>
> ```bash
> hermes config set model.provider deepseek
> hermes config set model.default deepseek-v4-flash
> # 内置 deepseek provider 自带 base_url=https://api.deepseek.com/v1 + DEEPSEEK_API_KEY（~/.hermes/.env），无需另设 base_url/api_key
> ```
>
> - 切换对**新会话/下一轮**生效；当前 TUI 会话需 `/reset` 或重开才切过去。Gateway（飞书/微信）走自己的 provider，不受影响。
> - **升级完成并验证后必须切回本地模型**：
>   ```bash
>   hermes config set model.provider lmstudio
>   hermes config set model.default qwen3.8-27b@q8_0
>   ```
>
> 若用户当前已在 DeepSeek（`hermes config get model` 显示 provider=deepseek），跳过 Step 0，升级后也无需切回。

```bash
# 1. Find the running AppImage process (NOT "lm-studio" — it's the AppImage path)
pgrep -af "LM-Studio\.AppImage" | grep -v grep

# 2. Kill the main process first
pkill -f "LM-Studio.AppImage" 2>/dev/null
sleep 1

# 3. Clean up residual crashpad handler (it keeps the old mount busy, blocking overwrite)
pkill -f "LM-Stu[A-Z]" 2>/dev/null || true
sleep 1

# 4. Verify no remaining LM Studio processes
pgrep -af "LM-Studio" || echo "✅ Clean"

# 5. Remove old AppImage BEFORE copying (cp can silently fail to overwrite
#    an in-use file — rm gives a clean slate)
rm -f ~/LM-Studio.AppImage

# 6. Copy new AppImage (wildcard works when only one file matches)
cp ~/下载/LM-Studio-*.AppImage ~/LM-Studio.AppImage
chmod +x ~/LM-Studio.AppImage

# 7. Verify copy integrity
ls -lh ~/LM-Studio.AppImage ~/下载/LM-Studio-*.AppImage
md5sum ~/LM-Studio.AppImage ~/下载/LM-Studio-*.AppImage

# 8. Launch new version
~/LM-Studio.AppImage --no-sandbox
```

### Background Launch (via shell)

```bash
nohup ~/LM-Studio.AppImage --no-sandbox > /dev/null 2>&1 &
```

In Hermes, use `terminal(background=true)` without `&`.

### Verify Version

### Hardlink Strategy for Mis-parented Download Directories

When LM Studio's built-in download places models in the wrong directory tree (e.g. Qwythos inside a Qwen directory), use hardlinks (`ln source target`) to share the file across both paths without 2x disk usage. The complete workflow (download → verify → hardlink fix → llama-server test → LM Studio integration) is documented in `references/model-download-verification.md`.

The exact version is visible in the crashpad process annotation:

```bash
ps aux | grep crashpad | grep LM | grep -v grep | tr ',' '\n' | grep _version
# Output: _version=0.4.17+4
```

### Backend Preference Format (v0.4.17+)

The backend config file `~/.lmstudio/.internal/backend-preferences-v1.json` changed format in LM Studio v0.4.17:

**Old format (v0.4.16 and earlier):**
```json
{"preferredBackend":"lm-hippo-cuda13","preferredBackendCUDAVersion":"13"}
```

**New format (v0.4.17+):**
```json
[
  {
    "model_format": "gguf",
    "name": "llama.cpp-linux-arm64-nvidia-cuda13",
    "version": "2.22.0"
  }
]
```

Always read the current file before writing — the version string may differ between releases.

### Data Persistence

| What | Path | Survives Upgrade? |
|------|------|-------------------|
| AppImage binary | `~/LM-Studio.AppImage` | **No** — replaced |
| Models + config | `~/.lmstudio/` | **Yes** — untouched |
| User settings | `~/.config/LM-Studio/` | **Yes** — untouched |

### Cleanup After Upgrade

```bash
# Remove the downloaded installer to free space
rm ~/下载/LM-Studio-*.AppImage
```

### Pitfalls

- **Always kill LM Studio before replacing the AppImage.** An in-use AppImage cannot be safely overwritten.
- **`--no-sandbox` is required** for Electron on systems without proper sandbox support (Ubuntu with AppImage).
- **Download directory may be localized** — on Chinese systems it's `~/下载/` instead of `~/Downloads/`. Check with `ls ~/下载/` or `xdg-user-dir DOWNLOAD`.
- **The AppImage path matters** if you have desktop shortcuts or autostart entries pointing to the old path. Keep it at `~/LM-Studio.AppImage` for consistency.

## Hermes Integration

### 通过 `hermes model` 交互式配置 (推荐)

在同一对话中切换到本地模型的推荐方式：

```bash
# 1）启动交互式模型选择器
hermes model
```

**交互式配置每一步的输入：**

| 步骤 | 显示 | 输入 |
|------|------|------|
| 1 | 提供者列表（默认 DeepSeek） | `30`（custom / direct API） |
| 2 | API base URL | `http://127.0.0.1:1234/v1` |
| 3 | API key | `not-needed` |
| 4 | API 兼容模式 | `1`（Auto-detect） |
| 5 | 确认检测到的模型 | `Y` |
| 6 | Context length | 直接回车（auto-detect） |
| 7 | Display name | `lmstudio` |

完成后配置保存为 `custom:lmstudio`，`hermes model` 退出。

> ⚠️ **当前对话不会切换到新模型。** 模型切换只在启动新 session 时生效。需要运行 `/reset` 或启动新的 `hermes` 实例。Gateway（飞书/微信）和 Cron 任务各自有独立的 model 配置，不会随 `hermes model` 切换。

### Basic — Single Model (手动配置)

Configure Hermes to use LM Studio as the main provider (OpenAI-compatible endpoint).

```bash
hermes config set model.provider lmstudio
hermes config set model.base_url http://127.0.0.1:1234/v1
hermes config set model.api_key "not-needed"     # LM Studio has no auth by default
hermes config set model.default <model-id>       # e.g. qwen3.8-27b@q8_0
```

> ⚠️ **必须用字面量 `provider: lmstudio`，不要用 `custom:lmstudio`。** 新版本 Hermes 内置识别 `lmstudio` provider（`agent/chat_completion_helpers.py` 中 `is_lmstudio = agent.provider == "lmstudio"`）——只有它能命中顶层 `reasoning_effort` 附加路径、能力探测（allowed_options）与免思考映射。若写成 `custom:lmstudio`，provider 字符串带 `custom:` 前缀，`is_lmstudio=False` → 不附加 `reasoning_effort`，思考关不掉。`custom:` 前缀的历史建议已过时。

Model IDs match what LM Studio's `/v1/models` returns（响应为 `models` 键，字段 `key`，与 `_lmstudio_entry_for` 按 key/id 匹配）。Verify with:
```bash
curl -s http://127.0.0.1:1234/v1/models
```

### 关闭本地 Qwen 思考（Hermes 侧自动附加 reasoning_effort）

Qwen3.x GGUF 默认 `reasoning_effort=xhigh`，每请求先耗 ~85–98 推理 tokens（感知慢的头号原因）。v0.4.23 后 API 层 `reasoning_effort: none` 已能真正关闭思考，Hermes 侧通过 per-model override 自动附加：

```bash
# 只针对本地 LM Studio 模型，不影响 DeepSeek 等生产 provider（它们无 override，走全局 agent.reasoning_effort: medium）
hermes config set agent.reasoning_overrides '{"qwen3.8-27b@q8_0": "none", "qwen3.6-27b": "none", "qwen3.5-35b-a3b": "none", "qwen3.6-35b-a3b": "none"}'
```

生效链路（已实测）：config `reasoning_overrides` → `resolve_reasoning_config` 返回 `{'enabled': False}` → transport（`agent/transports/chat_completions.py` 主请求 + iteration-summary 路径）在 `is_lmstudio and supports_reasoning` 时调用 `resolve_lmstudio_effort` → 顶层 `api_kwargs["reasoning_effort"] = "none"`。能力探测匹配 `/api/v1/models` 的 `capabilities.reasoning.allowed_options`（如 `["off","on"]`），`none` 在映射集合内 → 必定发送。

- 会话级临时覆盖：`/reasoning none`（session 级），`/reasoning none --global` 写入 config 全局（影响所有 provider，慎用）。
- config.yaml 改动经 mtime 缓存，gateway 下一轮自动生效，**无需重启** gateway；CLI 新会话立即生效。
- 验证：`python3 -c "import yaml; from hermes_constants import resolve_reasoning_config; print(resolve_reasoning_config(yaml.safe_load(open('$HOME/.hermes/config.yaml')), 'qwen3.8-27b@q8_0'))"` → `{'enabled': False}`。

### Dual-Model Routing (Local + Cloud)

Route daily/repetitive tasks to local LM Studio and complex tasks to a cloud provider via Hermes delegation:

```bash
# Main session → LM Studio (fast, local, for daily work)
hermes config set model.provider custom:lmstudio
hermes config set model.base_url http://127.0.0.1:1234/v1
hermes config set model.api_key "not-needed"
hermes config set model.default qwen/qwen3.6-27b

# Delegation (subagents) → cloud provider (for complex/capability-heavy tasks)
hermes config set delegation.provider deepseek
hermes config set delegation.model deepseek-v4-flash
hermes config set delegation.base_url https://api.deepseek.com/v1
```

How it works at runtime:
- **Main conversation** uses the local model (fast, zero-latency for daily Q&A, file ops, simple code)
- **`delegate_task` calls** automatically route to the cloud delegation model (more capable for debugging, research, complex refactors)
- The DEEPSEEK_API_KEY (or equivalent cloud provider key) must be set in `~/.hermes/.env`
- Config changes take effect after a session reset (`/reset` in CLI, or start a new `hermes` invocation)
- Switching between local and cloud affects only the current TUI session — gateway (飞书/微信) continues using its own configured provider

## Diagnosing Crashes & Freezes

When the system freezes, restarts, or the display server crashes during LM Studio inference:

### Step 1: Check Crash Reports
```bash
ls -lt /var/crash/                # apport crash reports
cat /var/crash/_usr_lib_xorg_Xorg.0.crash | strings | grep -iE "signal|crash|segfault|nvidia|oom" | head -10
```

### Step 2: Check LM Studio Server Logs
```bash
ls -lt ~/.lmstudio/server-logs/*/
cat ~/.lmstudio/server-logs/<date>/<logfile>.log
```

> ⚠️ Server logs contain full request bodies (tool schemas, message content) as JSON. Greps for engine keywords (`offload`, `n_ctx`) come back dominated by this noise — filter out lines starting with quotes/braces; engine startup lines may be absent from these logs entirely.

Look for:
- **mlock failures**: `"warning: failed to mlock ... Cannot allocate memory"` → need to increase memlock limit
- **Model load cancelled**: `"Model load request cancelled by client disconnect"` — loading took too long / OOM
- **Context warnings**: `"n_ctx_seq (N) < n_ctx_train (M)"` — model's native context much larger than configured
- **Prompt cache enabled**: `"prompt cache is enabled, size limit: N MiB"` — prompt cache consumes significant RAM

### Step 3: Check System Resources
```bash
free -h                          # memory usage
nvidia-smi                       # GPU memory (unified memory on GB10)
dmesg | tail -40                 # kernel messages (OOM, PCIe errors)
uptime                           # uptime — short uptime = recent crash
```

### Step 4: Compare Server Logs Across Versions (n_ctx Regression)

The most actionable diagnostic for "it worked before the update" crashes: **compare `n_ctx` in server logs** across versions.

```bash
# Check old and new server logs for n_ctx defaults
grep "n_ctx=" ~/.lmstudio/server-logs/2026-06/*.log | head -10
grep "n_ctx=" ~/.lmstudio/server-logs/2026-07/*.log | head -10
```

A jump like `n_ctx=8192 → n_ctx=262144` (32×) after a LM Studio update is a known regression pattern in llama.cpp 2.23.0+. This change alone can trigger GPU driver timeouts on unified-memory systems (GB10) even when total memory is sufficient, because the larger initial allocation takes longer and exceeds the GPU driver's timeout threshold.

When you find this, the fix is to manually set context length to a reasonable value (e.g. 32768 or 65536) in LM Studio's model settings rather than relying on the backend's inflated default.

### Step 5: Check LM Studio Config Files
```bash
~/.lmstudio/settings.json              # main settings, context length
~/.lmstudio/.internal/http-server-config.json  # JIT, auto-start, port
~/.lmstudio/.internal/model-data.json  # last loaded model
```

## Memory Optimization (Unified Memory Systems)

On NVIDIA GB10 (Grace Blackwell / Project DIGITS), CPU and GPU share the same **unified memory pool** (128GB total, ~121GB usable). OOM on unified memory can crash the entire SoC, not just the GPU — unlike discrete GPUs where CUDA just returns an error.

### Memory Budget Estimation

| Component | Approximate Size |
|-----------|-----------------|
| Model weights (Q4_K_M) | ~0.56 × parameter count (e.g., 120B → ~68GB) |
| Prompt cache | 8192 MiB by default (~8GB) |
| KV cache (4 slots × context N) | Varies by model architecture |
| LM Studio runtime (Electron) | ~3-5 GB |
| Xorg + GNOME desktop | ~3-4 GB |
| Other system processes | ~3-5 GB |

Leave at least **20-30GB headroom** on a 121GB system for stability.

### Configuration Optimization

#### Reduce Context Length
```bash
# Edit ~/.lmstudio/settings.json
"defaultContextLength": { "type": "custom", "value": 4096 }
```

#### Disable JIT Model Loading
```bash
# Edit ~/.lmstudio/.internal/http-server-config.json
"justInTimeModelLoading": false
```
- JIT on: model loads/unloads per request (saves idle memory, but load spikes can cause OOM)
- JIT off: model stays loaded (steady memory, faster inference, no load spike)

#### Increase memlock Limit (required for large models)
```bash
# Add to /etc/security/limits.conf (requires reboot)
* soft memlock unlimited
* hard memlock unlimited
```

#### Enable Model Loading Guardrails (prevents accidental huge loads)
Already in `settings.json`:
```json
"modelLoadingGuardrails": { "mode": "high", "customThresholdBytes": 4294967296, "alwaysAllowLoadAnyway": false }
```

#### Additional Safety Measures
- Close other memory-heavy apps (browser tabs, WeChat, etc.)
- Disable speculative decoding (`configPresetInclusiveness.speculativeDecoding: false`)

### Model Selection (GB10 Optimal Fit)

For detailed model combo recommendations including task-specific picks (coding vs reasoning vs English vs Chinese), Qwen3.6 vs Llama 3.3 decision tree, Q8_0 vs Q4_K_M tradeoffs, and per-hardware-class guides, see `references/model-combo-recommendations.md`.

For precise KV cache memory calculation at any context length, including the formula, model-architecture extraction from GGUF metadata, and verified dual-model budgets for Qwen3.6-27B + Qwen3.6-35B-A3B, see `references/context-sizing-gb10.md`.

### Model Selection (GB10 Optimal Fit)

| Model | Size on Disk | GPU Memory | Fit on GB10? | CUDA Speed | CPU Speed |
|-------|-------------|-------------|-------------|-----------|----------|
| Qwen3.6-27B (Q4_K_M) | ~16 GB | ~18 GB | ✅ Excellent | ~65 tok/s | ~25 tok/s |
| Qwen3.5-35B-A3B (Q4_K_M) | 20 GB | ~22 GB | ✅ Excellent | ~76 tok/s | ~30 tok/s |
| Qwen2.5-32B (Q4_K_M) | ~18 GB | ~20 GB | ✅ Excellent | ~50 tok/s | ~20 tok/s |
| Llama-3.1-70B (Q4_K_M) | ~40 GB | ~42 GB | ⚠️ Tight | ~25 tok/s | ~12 tok/s |
| Gemma-2-27B (Q4_K_M) | ~15 GB | ~17 GB | ✅ Excellent | ~60 tok/s | ~25 tok/s |
| Qwythos-9B-Claude-Mythos-5-1M (BF16) | 18 GB | ~20 GB | ✅ Good | ~50 tok/s | ~20 tok/s |
| Nemotron-3-Super-120B-A12B (Q3_K_M) | 64.65 GB | ~66 GB | ⚠️ OK with CUDA | ~20 tok/s | ~8 tok/s |
| Nemotron-3-Super-120B-A12B (Q4_K_M) | 86.98 GB | ~88 GB | ❌ OOM on CUDA | — | ~6 tok/s |

**For GB10 with CUDA backend:** models ≤ 65 GB on disk are safe (≥15GB headroom).
**For GB10 with CPU backend:** models up to 80 GB on disk work, but slow.
**Nemotron-3-Super sweet spot:** Q3_K_M (64.65GB) via bartowski or unsloth — use CUDA13 backend for ~20 tok/s.
**Qwythos-9B:** Only BF16 available (no Q4/Q8). 18GB is acceptable but leaves less headroom than a Q4 quant would. For tighter dual-model combos, look for community Q4_K_M quantizations on HuggingFace.

### Accelerated Model Downloads (China Network)

When HuggingFace is slow or blocked, use hf-mirror.com and aria2c for large GGUF downloads. See `references/model-download-china.md` for the full workflow covering discovery, download, and verification.

### Quick Download Commands

**Modern `hf` CLI (good for ≤5GB files):**
```bash
export HF_ENDPOINT=https://hf-mirror.com
hf download <user>/<model> <filename.gguf> --local-dir ~/.lmstudio/models/<user>/<model>/
```

**`aria2c` (recommended for large files ≥5GB, with multi-threaded resume):**
```bash
cd ~/.lmstudio/models/<user>/<model>/
aria2c -x 4 -s 4 --continue=true \
  --header="User-Agent: huggingface-hub/1.21.0" \
  -o "<filename.gguf>" \
  "https://hf-mirror.com/<user>/<model>/resolve/main/<filename.gguf>"
```

Leave aria2c running in a background terminal while continuing other work. Use `cronjob` or a periodic check for completion.

### Discovery
```bash
# Search models
curl -sL "https://hf-mirror.com/api/models?search=qwen+gguf&sort=downloads&direction=-1&limit=10"

# Get file sizes from README
curl -sL "https://hf-mirror.com/<user>/<model>/raw/main/README.md"

# Check available files and sizes
hf download <user>/<model> --dry-run
```

> 🔍 bartowski's quantizations always include a README with precise file sizes — [[readme](https://hf-mirror.com/bartowski/nvidia_Nemotron-3-Super-120B-A12B-GGUF/raw/main/README.md)].

> 🔍 **ModelScope is the fastest GGUF discovery path from mainland China** — no mirror needed. Use `https://www.modelscope.cn/api/v1/models/{owner}/{repo}/repo/files?Revision=master&Recursive=true` to list quant files with exact sizes, and `/api/v1/models/{owner}/{repo}` to probe repo existence. Full API, worked example, and Qwen3.8-27B size table in `references/modelscope-model-discovery.md`.

## CUDA vs CPU Backend on ARM64/GB10

**This is the #1 cause of "it worked before reinstall" crashes on NVIDIA GB10 (Project DIGITS/DGX Spark) — LM Studio auto-upgraded to a CUDA backend that can't handle large allocations on ARM64.**

### The Root Cause

On NVIDIA GB10 (ARM64, unified memory), LM Studio can use two different llama.cpp backends:

| Backend | Name | Memory Path | Stable for 80GB? |
|---------|------|-------------|-------------------|
| **CPU** | `llama.cpp-linux-arm64` | `mmap()` -> Linux page cache | Yes |
| **CUDA13** | `llama.cpp-linux-arm64-nvidia-cuda13` | `cudaMalloc()` -> NVIDIA driver -> **IOMMU mapping** | No |

On ARM64, the CUDA backend's large memory allocations go through the **IOMMU** (Input-Output Memory Management Unit). An 80GB IOMMU mapping can:
- Exhaust IOMMU page table entries
- Trigger fatal NVIDIA driver errors
- Cause Xorg to crash with **SIGABRT** (Signal 6) -> black screen -> system crash

The CPU backend uses standard `mmap()` which handles large allocations gracefully on unified memory — **all memory IS system memory** on GB10, so there is no performance penalty from the CPU backend for memory allocation itself (inference compute still uses GPU through llama.cpp's GPU offloading when available).

### Detecting the Backend

Check which backends LM Studio has installed and which is active:

```bash
# List installed backends
ls ~/.lmstudio/extensions/backends/

# Check current preference
cat ~/.lmstudio/.internal/backend-preferences-v1.json

# Compare GPU survey results
python3 -c "
import json
with open('$HOME/.lmstudio/.internal/internal-engine-index.json') as f:
    data = json.load(f)
for e in data['json']:
    m = e['manifest']
    survey = e['hardwareSurveyResult']['gpuSurveyResult']
    print(m['name'], 'v' + m['version'], ': GPU=', survey['result']['code'])
"
# Output: "NoDevicesFound" = CPU backend, "Success" = CUDA backend
```

### Switching Backend to CPU (Stable)

```bash
cat > ~/.lmstudio/.internal/backend-preferences-v1.json << 'EOF'
[
  {
    "model_format": "gguf",
    "name": "llama.cpp-linux-arm64",
    "version": "2.20.1"
  }
]
EOF
```

Then restart LM Studio. The model will load via `mmap()` — stable for 80GB+ models.

### Switching Backend Back to CUDA13 (For Smaller Models)

```bash
cat > ~/.lmstudio/.internal/backend-preferences-v1.json << 'EOF'
[
  {
    "model_format": "gguf",
    "name": "llama.cpp-linux-arm64-nvidia-cuda13",
    "version": "2.22.0"
  }
]
EOF
```

### When to Use Each Backend

- **CPU backend**: When loading models >65GB on GB10. Stable but slower. Use `llama.cpp-linux-arm64`.
- **CUDA backend**: When using models <=65GB (e.g. Qwen3.5-35B-A3B at 20GB, Nemotron-3-Super Q3_K_M at 64.65GB). Faster inference (~20 tok/s for 120B MoE), stable when memory has >=15GB headroom.
- **Threshold rule of thumb**: If the model file size is >75% of total unified memory (~80GB), use CPU backend. If <=75%, CUDA is safe.
- **If it worked before a system reinstall**: LM Studio likely upgraded from CPU to CUDA backend during reinstall/setup. The old system was using the CPU backend without your knowledge.

## Model Lifecycle (REST API)

LM Studio's native API at `/api/v1/` can load/unload models without restarting the GUI. Speed measurement and slow-inference diagnosis workflows live in `references/model-deletion-and-speed-measurement.md`.

### Check Available Models (Native API)

```bash
curl -s http://127.0.0.1:1234/api/v1/models | python3 -m json.tool
```

Shows all installed models, their quantization variants, and current `loaded_instances`.

### Load a Model

```bash
curl -s -X POST http://127.0.0.1:1234/api/v1/models/load \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen/qwen3.5-35b-a3b"}'
```

Response includes `load_time_seconds` and `"status": "loaded"`. Loading a model that's already loaded is a no-op (re-uses the instance).

When JIT (just-in-time model loading) is disabled in `http-server-config.json`, the model stays loaded until explicitly unloaded or LM Studio exits. With JIT enabled, models load/unload per request — convenient for multi-model workflows but risks OOM on load spikes.

### Unload a Model

```bash
curl -s -X POST http://127.0.0.1:1234/api/v1/models/unload \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen/qwen3.5-35b-a3b"}'
```

Useful before loading a different large model to free unified memory.

### Override Context Length

```bash
curl -s -X POST http://127.0.0.1:1234/api/v1/models/load \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen/qwen3.5-35b-a3b","configOverrides":{"defaultContextLength":16384}}'
```

Useful for temporarily reducing context on memory-constrained systems without editing `settings.json`.

## DGX Spark First-Boot Configuration

The NVIDIA DGX Spark (GB10) factory image ships with first-boot services that configure platform-specific optimizations. After a fresh Ubuntu install these condition markers are lost — the GRUB configs are still applied from package files, but confirming the setup status helps rule out misconfiguration.

```bash
# Check which first-boot markers exist (empty = not run)
ls /var/tmp/first-boot-* 2>/dev/null || echo "No markers found"

# Manually trigger a first-boot service
sudo touch /var/tmp/first-boot-nvidia-disable-numa-balancing
sudo systemctl start nvidia-disable-numa-balancing.service
```

Key services: `nvidia-disable-numa-balancing`, `nvidia-disable-init-on-alloc`, `nvidia-configure-iommu-pt`, `nvidia-enable-power-meter-cap`.

## Pitfalls

- **Model not showing in UI after external GGUF download.** If a GGUF file was placed in `~/.lmstudio/models/` via aria2c, hf CLI, or manual copy and LM Studio does not show it (or shows "修复下载" / "no models available"), the issue is **not cache misalignment** but LM Studio's three-tier model state architecture: (i) GGUF files on disk, (ii) hub virtual model registration at `~/.lmstudio/hub/models/`, and (iii) download tracking in `download-jobs-info.json`. All three tiers must agree. A GGUF file on disk without matching hub registration + download tracking will never appear in the UI. See `references/model-variant-detection.md` for the full debugging workflow, list of every attempted fix that does NOT work and why, and the recommended alternatives.

  **TL;DR:** LM Studio is a managed model environment, not a raw GGUF browser. Reliable fixes in descending order:
  1. **Use LM Studio's built-in download** — always works, all tiers stay in sync.
  2. **Run llama-server directly** — bypasses LM Studio's model management entirely using the bundled llama.cpp backends in `~/.lmstudio/extensions/backends/` on a separate port.
  3. **Accept any variant re-download** that LM Studio performs — the re-downloaded GGUF may differ slightly in size but is functionally equivalent.

- **Hub auto-redownload after deleting GGUF files.** LM Studio's `~/.lmstudio/hub/models/<user>/<model>/` virtual model registrations can trigger **automatic HuggingFace downloads** when the model directories are restored after a GGUF file removal. If you delete a GGUF variant that belongs to a registered virtual model, and the hub registration is present, LM Studio may silently re-download the file on next startup. Observed in practice: a removed 20GB Q4 was re-downloaded as a 19.72GB variant. To avoid this: (a) first remove/rename the hub registration directory, (b) then delete the GGUF, (c) optionally restore the hub registration if you want the virtual model wrapper back. If step (c) triggers a re-download, accept it or keep the hub registration permanently removed.
- **Jinja template error with empty/fresh conversation.** Some Qwen GGUF quantizations fail with `"No user query found in messages"` on the **first message** of a fresh session. The root cause is the Qwen chat template failing to detect the user message role in a new conversation context. This error can be **misleading** in gateway setups: if the TUI session fails with this error, the gateway session (using a different provider like DeepSeek) is **unaffected** and replies normally, but the user sees the TUI error and the gateway's reply side-by-side, assuming both are from the same session. The `systematic-debugging` reference `diagnosing-cross-session-error-illusion.md` covers how to disambiguate this. Recovery: restart the TUI session (`/reset` in Hermes CLI or close/reopen the TUI tab); if the inference engine hangs after this error, kill and restart LM Studio entirely (`killall -9 lm-studio && ~/LM-Studio.AppImage --no-sandbox`).
- **NEVER set context_length beyond hardware limits on unified memory.** A single request with inflated context (e.g. 64K on Nemotron-120B) can trigger instant OOM and system crash.
- **Prompt cache is ~8GB by default** and cannot be disabled through LM Studio's exposed config. Only reduce context length to lower KV cache overhead.
- **Memlock changes require logout/reboot** (`ulimit -l` only shows the change after re-login).
- **Xorg SIGABRT crash** (Signal 6) is the symptom, not the cause — root causes are memory exhaustion or IOMMU mapping failure.
- **"Just-in-time" model loading** can paradoxically make things worse on unified memory: the load spike is the most memory-intensive moment. Prefer JIT off for steady-state workloads.
- `modelLoadingGuardrails` only warns — the user can bypass. Always double-check context_length settings.
- **The CUDA backend on ARM64 is the default** when LM Studio detects an NVIDIA GPU. If you have stability issues with large models, switch to the CPU backend first before assuming it is a hardware fault.
- **"It worked before the reinstall"** is the #1 diagnostic clue. LM Studio's CUDA backend may not have been active before, or an older LM Studio version used a different memory allocation path.
- **n_ctx default can jump 32× between llama.cpp versions.** Backend versions 2.22.0 and earlier default to 8192; 2.23.0+ defaults to model-native max (often 262144). This inflated default can trigger GPU driver timeouts on unified-memory systems even when total memory is sufficient. **Always check `n_ctx` in server logs** after an LM Studio update that causes new stability issues. The fix is manual context length reduction in model settings, not a backend downgrade.
- **A request that causes a jinja template error** ("No user query found in messages") can hang the inference engine. Symptoms: HTTP server responds to `/health` but `/v1/models` returns `{"data":[]}` (no loaded instances) and `/v1/chat/completions` times out. Recovery: kill all lm-studio processes (`killall -9 lm-studio`) and restart.
- **Dual-model crash root cause is KV cache, not weights.** On GB10, model weights that individually fit can still crash when loaded together at high context length. The KV cache grows linearly with context: a 128K context on two models can add 30-50GB of KV cache on top of weights. **Keep context ≤ 32K for dual-model safety.** See `references/context-sizing-gb10.md` for exact calculations per model combo.
- **Thinking-type models are the #1 cause of perceived slowness — not vision, not GPU.** Qwen3.x GGUFs default to `reasoning_effort=xhigh` and emit ~85–98 reasoning tokens per request before any visible content (~8s at 27B Q8_0 speed). **v0.4.18 ignored every API-level control** (`enable_thinking`, `/no_think`, top-level `reasoning_effort`, `chat_template_kwargs.reasoning_effort`) — verified A/B. **v0.4.23+ FIXED this: top-level `reasoning_effort: "none"` (and presumably low/medium) now genuinely disables thinking** — verified A/B on qwen3.6-35b-a3b Q8_0: `none` → direct answer in 0.54s with 0 reasoning tokens vs default → 3.7–10s with all tokens consumed by reasoning. `enable_thinking: false` still does NOT work in v0.4.23 — use `reasoning_effort`. Diagnose with the prefill/thinking separation workflow in `references/model-deletion-and-speed-measurement.md`.

## Verification

After optimization:
```bash
# Check memory available
free -h

# Check LM Studio is running and serving
curl -s http://127.0.0.1:1234/v1/models | python3 -m json.tool

# Quick inference test
curl -s http://127.0.0.1:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen/qwen3.5-35b-a3b","messages":[{"role":"user","content":"Hi"}],"max_tokens":20}'
```
