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
> hermes config set model.default deepseek-flash
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
hermes config set delegation.model deepseek-flash
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

### 配置文件编辑协议（必守）

改 `settings.json` / `http-server-config.json` 必须走 **停 → 改 → 启**：运行中改会被 App 回写覆盖。且**整个文件必须通过 Zod 校验，否则全文件被拒、所有键回退默认**——不是只丢弃非法的那一个键。典型后果：`fileLoggingMode` 写成非枚举值 → `autoStartOnLaunch` 被打回默认 → API 1234 不再随 App 启动。

```bash
systemctl --user stop lmstudio-gui 2>/dev/null || pkill -f "LM-Studio.AppImage"
for i in $(seq 1 20); do ss -tlnp | grep -q ':1234' || break; sleep 1; done   # 等端口释放
cp ~/.lmstudio/settings.json ~/.lmstudio/settings.json.bak-$(date +%Y%m%d-%H%M%S)   # 改前必备份
# ...改文件...
# 用 systemd-run 起（Hermes 的 terminal 不接受 nohup/setsid/&）；App stdout 是唯一能看到 ZodError 的地方
systemd-run --user --unit=lmstudio-gui --collect \
  --property=StandardOutput=append:/tmp/lmstudio-start.log \
  --property=StandardError=append:/tmp/lmstudio-start.log \
  --setenv=DISPLAY=:10.0 --setenv=XDG_RUNTIME_DIR=/run/user/1000 --setenv=HOME=/home/bobobears \
  --setenv=PATH=/home/bobobears/.lmstudio/bin:/usr/local/bin:/usr/bin:/bin \
  /home/bobobears/LM-Studio.AppImage --no-sandbox
curl -s http://127.0.0.1:1234/v1/models >/dev/null && echo "API 就绪（冷启动约 3s）"
grep -c ZodError /tmp/lmstudio-start.log    # 必须为 0；server-logs/ 里看不到这个错
```

**已实测的合法取值（写错即全文件被拒）：**

| 文件 | 键 | 合法值 | 语义 |
|------|----|--------|------|
| settings.json | `defaultContextLength` | `{"type":"max"\|"custom","value":<int>}` | `max` = 模型原生上限（Qwen3.8-27B = 262144，即崩溃触发器）；`custom` = 固定值 |
| settings.json | `developer.autoUpdateExtensionPacks` | bool | 后端自动更新；App 启动可能重写，改完启一次后要复核 |
| settings.json | `developer.autoDeleteExtensionPacks` | bool | 自动删旧后端（旧版本目录就是被它清掉的） |
| http-server-config.json | `fileLoggingMode` | `off`/`succinct`/`full` | **没有 "verbose"** |
| http-server-config.json | `justInTimeModelLoading` | bool | 必须与 Hermes `model.lmstudio_load_mode: jit` 成对 |
| http-server-config.json | `autoStartOnLaunch` | bool | 随 App 启动 HTTP 服务（关掉就得手动 `lms server start`） |
| http-server-config.json | `networkInterface` | `127.0.0.1` / `0.0.0.0` | 只本机 / 局域网可见 |

### 加载前的内存预检（必守）

在这台 GB10（统一内存 121GiB，`nvidia-smi` 显存字段报 N/A）上，**内存不足时加载模型会挂死整机**，不是普通的加载失败：

- 故障链：系统内存已被占满 → 加载 30GB 模型 + 全量 GPU 卸载（`n_gpu_layers=999999`，即 gpuOffload=auto）→ llama.cpp 报 `common_fit_params: failed to fit params to free device memory ... abort`（这步本身安全）→ 但内核同时报 `NVRM: nvCheckOkFailedNoLog: Check failed: Out of memory [NV_ERR_NO_MEMORY] ... _memdescAllocInternal @ mem_desc.c` → **整机硬挂起，必须断电重启**。
- **特征**：LM Studio 日志与内核日志同时戛然而止、无 systemd 关机流程、重启后 `/var/crash/kdump_lock` 存在但无 vmcore；`journalctl -b -1` 末尾只剩 `Under memory pressure, flushing caches`。
- **规则**：触发任何模型加载（含 JIT 请求）之前先跑 `free -g`，**可用内存 < 55GB 就不加载**——先 `lms unload --all` 或等内存释放。（本机已自动化：`llama-run.sh` 预检拒载 + `mem-guard.timer` 分级处置，见「本机现行架构」）
- 常见内存黑洞：Hermes 桌面 App 的 python 后端曾膨胀到 86–90GB 被 OOM-killer 连杀三次，把系统压在 critical 水位（`journalctl -b -1 | grep oom-kill`）；处理 300MB+ 大文件（崩溃转储、全量日志）前先留意内存。
- 取证命令：`journalctl -b -1 | grep -iE "NVRM|Xid|oom-kill|failed to fit"`；`grep -hE "failed to fit|out of memory|abort" <LM Studio stdout 日志>`。

### 远程访问本地模型的两种方式

- `networkInterface: "0.0.0.0"` = 局域网直连 `http://<本机IP>:1234/v1`。**LM Studio HTTP 服务无任何鉴权**，等于局域网内所有设备都能无凭证调用（本机 ufw 是 `ENABLED=no`，并不拦截），仅在确需时开启。
- 推荐：保持 `127.0.0.1` + Dell 侧建 SSH 隧道 `ssh -N -L 1234:127.0.0.1:1234 bobobears@192.168.31.149`，客户端指向 `http://127.0.0.1:1234/v1`（端口不对外暴露，只有隧道方可用）。
- 客户端必须显式带 `"reasoning_effort": "none"`，否则 Qwen3.8 的思考链会吃光 token、`content` 返回空字符串（实测：默认 400 tokens 全是 `reasoning_tokens`、content 空；加 none 后 0 思考 token、1 秒出答案）。

### 每模型加载配置落盘点

`~/.lmstudio/.internal/user-concrete-model-default-config/<model>/` 的 `load.fields` 为空 ⇒ **UI 里手改的 GPU 卸载层数从未落盘**，重启即回 `numGpuLayers = -1`（auto → 999999 全量卸载）。不要再试图钉住"30 层"：GB10 统一显存 121.69 GiB，实测 auto 全量卸载 + 27B Q8_0（29.98GB）+ ctx 65536 仅 9 秒加载、加载期最低可用内存 81.7 GiB，全量卸载就是本机最优。卸载层数在**任何日志与 API 里都不暴露**（full 模式也不含 llama.cpp 原始 offload 行），只能用加载耗时与 `lms ps` 的 DEVICE=Local 间接判断。

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

#### Context Length（本机已验证：custom 65536，绝不用 max）
```bash
# ~/.lmstudio/settings.json
"defaultContextLength": { "type": "custom", "value": 65536 }
```
- KV 成本：Qwen3.8-27B ≈ **68 KiB/token**（hybrid 架构，每 4 层 1 层全注意力）→ 65536 ≈ 4.25 GiB；262144 ≈ 17 GiB。
- 65536 与 Hermes 侧 `providers.lmstudio.context_length` 对齐即可覆盖日常长文档；再大只是白吃内存。
- **`type: "max"`（=262144）是本机崩溃的真凶**，不是"显存不够"。

#### Just-in-Time 加载（本机选 on，与 Hermes 成对）
```bash
# ~/.lmstudio/.internal/http-server-config.json
"justInTimeModelLoading": true
```
- Hermes `model.lmstudio_load_mode: jit` 时**跳过预加载**，全靠 LM Studio 自动加载；若这里为 false 则调用链断裂（请求打不到任何已加载实例）→ 二者必须同时为 jit/true。
- 实测：清空实例后直接 `POST /v1/chat/completions` 触发按需加载，首次请求总耗时 16s（含加载），`jitModelTTL` 60m 内后续请求不再加载。
- 验证时 `max_tokens ≥ 300`：Qwen3.8 默认思考，token 预算会被 `reasoning_tokens` 吃光，`content` 返回空字符串——看着像失败，其实链路正常（首次测试就踩了这个）。

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

## 脱离 LM Studio 直接跑 llama-server（实测）

LM Studio 的推理引擎就是 llama.cpp——它的后端目录里就带着官方 `llama-server` 二进制，可直接复用，不必另装：
`~/.lmstudio/extensions/backends/llama.cpp-linux-arm64-nvidia-cuda13-<ver>/llama-server`
（必须 `LD_LIBRARY_PATH` 指向同目录，否则找不到 `libllama*.so`；`--version` 报 `0.5.0-dev`）。

```bash
D=$HOME/.lmstudio/extensions/backends/llama.cpp-linux-arm64-nvidia-cuda13-2.46.0
LD_LIBRARY_PATH="$D" "$D/llama-server" -m <model.gguf> --host 127.0.0.1 --port 1235 \
  -c 65536 -np 1 --fit on -fa on -ctk q8_0 -ctv q8_0 --alias qwen3.8-27b --api-key <key> -rea off
```

必守要点（GB10 实测事实）：

- **`--fit on`（默认）比 LM Studio 更安全**：LM Studio 硬写 `-ngl 999999`，内存不足时 `common_fit_params` 只能 `abort`；不指定 `-ngl` 而留给 `--fit`，llama.cpp 会自动调整层数以适应设备内存（慢而不死）。
- **`-np` 默认 `auto`（实测取 4）**，而 `n_ctx_slot` 按 `-c` 逐 slot 计 → 不显式写 `-np 1` 会让 KV 缓存 ×4。
- **systemd `MemoryMax` 保护不了模型内存**（实测：`MemoryMax=20G` 下 27GB 模型照样加载成功，`MemoryCurrent` 仅 1.87GB）。权重走 CUDA 驱动分配（`-v` 日志里的 `dev = CUDA0`），不计入进程 memcg。**不要指望 cgroup 上限防“加载时 OOM”**，只能靠加载前的 `free` 预检。
- 加载耗时：冷读盘 33s，页缓存命中 4–6s；推理吞吐约 8.5 tok/s（27B Q8，接近 GB10 带宽上限，正常）。
- 自带 `--api-key` / `--alias` / `-rea off`（服务端默认关思考，客户端无需再传 `reasoning_effort`），比 LM Studio 可控；代价是无模型下载管理界面，且模型常驻内存（LM Studio 的 JIT 空闲时不占）。
- **本机这个 llama.cpp 构建没有可用的 WebUI**：`GET http://127.0.0.1:1234/` 返回 **404**（74 字节）。调用只能走 OpenAI 兼容端点（`/v1/models`、`/v1/chat/completions`、`/health`）或 llama.cpp 原生端点。别向用户承诺“浏览器打开就有界面”。
- 与 LM Studio 同实例互斥：同时只应该让一个引擎持有模型（内存，不是端口）。

## 本机现行架构：独立 llama-server + 内存看门狗（已弃用 LM Studio）

LM Studio 已停用（无 systemd 单元、无 autostart，不会自己回来）。本地推理改由 systemd 用户服务直接托管 llama.cpp：

| 组件 | 路径 / 单元 | 作用 |
|------|-------------|------|
| 引擎 | `~/.local/share/llama.cpp/llama-server`（含 `libllama*.so`） | 从 LM Studio 后端目录 `cp -a` 复制，脱离 App 自动更新 |
| 模型 | `~/models/qwen3.8-27b/Qwen3.8-27B-Q8_0.gguf` | 已移出 `~/.lmstudio/models/` |
| 服务 | `llama-server.service`（user，enabled） | `127.0.0.1:1234`，别名 `qwen3.8-27b@q8_0,qwen3.8-27b`，`-np 1`、`--fit on`、`-rea off` |
| 启动包装 | `~/.local/bin/llama-run.sh` | 先跑预检，再 `exec` 引擎 |
| 加载预检 | `~/.local/bin/mem-precheck.sh` | 可用内存 < 55GiB → 退出码 78，拒绝加载 |
| 看门狗 | `mem-guard.timer` + `mem-guard.service`（user，enabled） | 每分钟采样统一内存并分级处置 |

看门狗分级（每个阈值都有同名环境变量可覆盖，便于测试）：

| 可用内存 | 动作 |
|----------|------|
| < 55GiB | 飞书告警（级别变化时，或同级每 30 分钟重复一次） |
| < 30GiB | `systemctl --user stop llama-server`（释放约 35GiB）+ 告警 |
| < 10GiB | 终止 RSS > 20GiB 的最大进程（防重演整机硬挂）+ 告警 |
| > 75GiB 且最大进程 < 15GiB 且距上次重启 > 30min | 自动重启 llama-server |

- 告警走 `hermes send --to feishu --quiet`：复用网关凭据，不经 LLM、不依赖网关进程是否在跑；加 `--json` 会返回 `message_id`，可用于验证真的投递了。日志 `~/.hermes/logs/mem-guard.log`（每分钟一行采样，超 3000 行自动轮转），状态 `~/.hermes/state/mem-guard.state`。
- 测试开关：`--simulate <MiB>` 只演算不动手、`--test-notify` 推测试消息、`--status` 看现状；`NOTIFY=0 MIN_AVAIL_MB=<n>` 可关推送 / 改预检门槛。
- 写这类后台脚本必须用「输出写文件 + read_file」取全量：Hermes 的 terminal 会把多行输出压成「1 lines output」，日志/取证类命令直接管道 `sed` 会丢内容。

### 在 Hermes 里切到本地 llama-server（实测流程）

```bash
hermes config set model.provider lmstudio          # 会自动清掉 model.base_url（它属于 deepseek）
hermes config set model.default qwen3.8-27b@q8_0
hermes config set model.context_length 65536       # 必做！见下
```

- **`model.context_length` 必须跟着改**：它是全局生效的那个，会盖过 `providers.lmstudio.context_length`。忘了改会留着上一个 provider 的值（如 DeepSeek 的 128000），而 llama-server 只服务 65536 → 长请求直接超窗报错。
- **服务端 `-c` 与 Hermes `model.context_length` 必须逐字相等**（本机踩过：服务单元写 `-c 32768` 而 Hermes 写 65536）。Hermes 按自己的 `context_length` 组织请求，服务端只按 `-c` 收；Hermes 侧偏大 → llama-server 报 `request (34144 tokens) exceeds the available context size (32768 tokens)` 并拒收，Hermes 压缩也救不回来 → 抛 `context_overflow` 把会话踢回云端 provider。改任一侧都要同步改另一侧。
  - 方向选大不选小：系统提示 + AGENTS.md 实占约 **27.6k tokens**，`-c 32768` 只剩 5k 给对话，等于不可用。本机定为两侧 **65536**（KV 走 `-ctk/-ctv q8_0` 量化，加载后 available 仍有约 85GiB）。
  - 复核命令：`curl -s http://127.0.0.1:1234/props | python3 -c "import sys,json;print(json.load(sys.stdin)['default_generation_settings']['n_ctx'])"` 应等于 `model.context_length`。
  - **回归验证必须真跨过旧门槛，并用服务端回读的数字证明**：发一个大请求后读回 `usage.prompt_tokens` 确认它 **> 旧值**，不要按“字符数 ÷ 4”估算——英数混排实测约 4.6 字符/token，估出来的请求会得到一个 23029 tokens 的“通过”假象（而真门槛是 32768），测试通过了却根本没触发过故障。阈值类修复一律要求：先确认输入触发了旧条件，再声称已修复。
- **`model.lmstudio_load_mode: jit` 要保留**：Hermes 只有在 `explicit` 时才会调 LM Studio 的管理 API 预加载模型（`run_agent.py:485`）。独立 llama-server 没这套接口，设成 `explicit` 会白等/报错；`jit` 表示直接打 OpenAI 端点。
- **端到端验证用 `hermes chat -q "…"`**（单次查询，非交互）：成功表现 = 回答正确 **且** `journalctl --user -u llama-server` 里出现 `POST /v1/chat/completions` + `slot print_timing`（实测 8.1–8.5 tok/s）。
- **成本预期**：agent 系统提示 + AGENTS.md 实占 **约 27.6k tokens**（65356 窗口的一半），首轮 prefill 约 38s（723 tok/s），后续靠前缀缓存才快；生成固定 8 tok/s。适合低频/批量任务，不适合高频对话。
- **作用范围**：`model.*` 是全局默认，飞书/微信/企微网关都跟随（它们没有 model 覆盖）——但 **hermes-gateway 只在启动时读配置**，不重启则仍用旧 provider；重启会打断运行中的 cron 任务。桌面端新开会话即生效，已开的会话沿用启动时的模型。**已显式 pin `provider`+`model` 的 cron 任务不跟随全局**（`hermes cron edit <id> --model <id>` 即 pin），也不会被 drift 保护跳过——把全局切到本地慢模型时它们仍走云端，这是预期行为，别当成故障去“修”。
- 切回：`hermes config set model.provider deepseek && hermes config set model.default deepseek-flash && hermes config set model.context_length 128000`。

### systemd 坑：RestartPreventExitStatus 只看「主进程」的退出码

想让"预检不过就停住、别每 15s 重试"生效，**预检不能放在 `ExecStartPre`**：那时主进程还没启动，`ExecMainStatus=0`，`RestartPreventExitStatus=78` 匹配不上 → 实测服务每 15s 无限重试（`NRestarts` 递增、日志刷屏）。正确做法是包一层脚本：预检失败 `exit 78`，成功则 `exec` 引擎——预检码成为主进程退出码，规则才真正生效（实测 `NRestarts=0`、`Result=exit-code`、`ExecMainStatus=78`、服务停在 failed 等人处理）。另建议 `StartLimitIntervalSec=300` + `StartLimitBurst=3` 兜底其它原因的启动风暴。

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
- **"Just-in-time" model loading** 的加载瞬间确实是最吃内存的时刻，但 2026-09 在本机实测：JIT on + ctx 65536 + auto 全量卸载稳定（首次请求 16s 含加载，最低可用内存仍有 81.7 GiB）。真正致命的是被 `defaultContextLength.type:"max"` 顶到 262144，不要把锅算在 JIT 头上。
- **Hermes `fallback_providers` 必须是 YAML 列表**，写成 JSON 字符串会被 `_iter_fallback_entries` 静默忽略（它只接受 dict/list）→ 一条永不生效的死配置。写成 `[{provider: custom, model: '<id>', base_url: 'http://127.0.0.1:1234/v1'}]`，并用 `hermes_cli.fallback_config.get_fallback_chain()` 复核解析结果。
- **本地模型 id 形如 `qwen3.8-27b@q8_0`**（含量化后缀）。引用前先 `curl -s http://127.0.0.1:1234/v1/models` 取真实 id——过期的 id（如 `qwen/qwen3.6-27b`、`qwen/qwen3.5-35b-a3b`）在 `default_model`/fallback 里会造成调用直接失败。
- **云 provider 的 id 同理：写进 config 前先问 provider 自己，看 `name` 字段而不是凭印象追版本号**：`curl -s <base_url>/models -H "Authorization: Bearer $KEY"`。厂商会把版本号从公开 id 里删掉、只留在 `name` 里——DeepSeek 现在只报两个 id：`deepseek-flash`（`name: DeepSeek-V4.1-Flash`，1M 上下文、支持图像输入）与 `deepseek-v4-pro`；用户在下拉菜单里找不到“V4.1”就是因为下拉用的是官方 id。旧版号 id（`deepseek-v4-flash`）仍被服务端静默别名，但别依赖它；`deepseek-chat` / `deepseek-reasoner` 已退役，靠 Hermes 本地重映射表（`hermes_cli/model_normalize.py`）兜底。验证别名是否还有效：发一个带该 id 的最小请求，看响应里的 `model` 字段被路由到了谁。改 id 时同步扫一遍 `config.yaml` 与 `cron/jobs.json`（`grep -n`），别只改一处。
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
