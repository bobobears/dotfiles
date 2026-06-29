---
name: lm-studio
description: "Configure, optimize, and troubleshoot LM Studio local inference server — memory tuning, crash/deadlock diagnosis, unified-memory systems (NVIDIA GB10/Project DIGITS), context sizing, and Hermes integration."
version: 1.7.0
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

```bash
# 1. Kill running LM Studio
killall lm-studio

# 2. Force kill if still running
killall -9 lm-studio

# 3. Replace AppImage (config/models in ~/.lmstudio/ persist)
cp ~/下载/LM-Studio-*.AppImage ~/LM-Studio.AppImage
chmod +x ~/LM-Studio.AppImage

# 4. Launch new version
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

### Basic — Single Model

Configure Hermes to use LM Studio as the main provider:

```bash
hermes config set model.provider lmstudio
hermes config set model.base_url http://127.0.0.1:1234/v1
hermes config set model.default <model-id>   # e.g. nvidia/nemotron-3-super or qwen/qwen3.5-35b-a3b
```

Model IDs match what LM Studio's `/v1/models` returns.

### Dual-Model Routing (Local + Cloud)

Route daily/repetitive tasks to local LM Studio and complex tasks to a cloud provider via Hermes delegation:

```bash
# Main session → LM Studio (fast, local, for daily work)
hermes config set model.provider lmstudio
hermes config set model.base_url http://127.0.0.1:1234/v1
hermes config set model.default qwen/qwen3.5-35b-a3b

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

### Step 4: Check LM Studio Config Files
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

### Model Selection (GB10 Optimal Fit)

| Model | Size on Disk | GPU Memory | Fit on GB10? | CUDA Speed | CPU Speed |
|-------|-------------|-------------|-------------|-----------|----------|
| Qwen3.5-35B-A3B (Q4_K_M) | 20 GB | ~22 GB | ✅ Excellent | ~76 tok/s | ~30 tok/s |
| Qwen2.5-32B (Q4_K_M) | ~18 GB | ~20 GB | ✅ Excellent | ~50 tok/s | ~20 tok/s |
| Llama-3.1-70B (Q4_K_M) | ~40 GB | ~42 GB | ⚠️ Tight | ~25 tok/s | ~12 tok/s |
| Gemma-2-27B (Q4_K_M) | ~15 GB | ~17 GB | ✅ Excellent | ~60 tok/s | ~25 tok/s |
| Nemotron-3-Super-120B-A12B (Q3_K_M) | 64.65 GB | ~66 GB | ⚠️ OK with CUDA | ~20 tok/s | ~8 tok/s |
| Nemotron-3-Super-120B-A12B (Q4_K_M) | 86.98 GB | ~88 GB | ❌ OOM on CUDA | — | ~6 tok/s |

**For GB10 with CUDA backend:** models ≤ 65 GB on disk are safe (≥15GB headroom).
**For GB10 with CPU backend:** models up to 80 GB on disk work, but slow.
**Nemotron-3-Super sweet spot:** Q3_K_M (64.65GB) via bartowski or unsloth — use CUDA13 backend for ~20 tok/s.

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

LM Studio's native API at `/api/v1/` can load/unload models without restarting the GUI.

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
- **Jinja template error with system messages.** Some Qwen GGUF quantizations may fail with "No user query found in messages" when the first message is a system role. This is a model-specific chat template issue — try using `lmstudio-community/` variants which have fixed prompt templates, or restart LM Studio and retry.
- **NEVER set context_length beyond hardware limits on unified memory.** A single request with inflated context (e.g. 64K on Nemotron-120B) can trigger instant OOM and system crash.
- **Prompt cache is ~8GB by default** and cannot be disabled through LM Studio's exposed config. Only reduce context length to lower KV cache overhead.
- **Memlock changes require logout/reboot** (`ulimit -l` only shows the change after re-login).
- **Xorg SIGABRT crash** (Signal 6) is the symptom, not the cause — root causes are memory exhaustion or IOMMU mapping failure.
- **"Just-in-time" model loading** can paradoxically make things worse on unified memory: the load spike is the most memory-intensive moment. Prefer JIT off for steady-state workloads.
- `modelLoadingGuardrails` only warns — the user can bypass. Always double-check context_length settings.
- **The CUDA backend on ARM64 is the default** when LM Studio detects an NVIDIA GPU. If you have stability issues with large models, switch to the CPU backend first before assuming it is a hardware fault.
- **"It worked before the reinstall"** is the #1 diagnostic clue. LM Studio's CUDA backend may not have been active before, or an older LM Studio version used a different memory allocation path.
- **A request that causes a jinja template error** ("No user query found in messages") can hang the inference engine. Symptoms: HTTP server responds to `/health` but `/v1/models` returns `{"data":[]}` (no loaded instances) and `/v1/chat/completions` times out. Recovery: kill all lm-studio processes (`killall -9 lm-studio`) and restart.

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
