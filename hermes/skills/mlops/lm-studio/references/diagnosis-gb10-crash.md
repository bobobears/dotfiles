# LM Studio Crash Diagnosis Reference

From a live diagnosis session on NVIDIA GB10 (Project DIGITS / DGX Spark) running Ubuntu 24.04 with LM Studio llama.cpp backends.

## System Profile Detected

- **Platform**: `aarch64` (ARM64), kernel `6.17.0-1014-nvidia`
- **GPU**: NVIDIA GB10 (Grace Blackwell superchip, unified memory)
- **Total Memory**: 127 GB → ~121 GB usable (`MemTotal: 127601388 kB`)
- **Swap**: 15 GB (unused)
- **Driver**: NVIDIA 580.142, CUDA 13.0
- **nvidia-smi**: `"Not Supported"` for VRAM display (unified memory — no separate VRAM counter)

## Key Diagnostic Commands Used

### Check Uptime (confirms recent crash)
```bash
uptime
# "up 3 min" = just rebooted
```

### Memory Status
```bash
free -h
# Before killing LM Studio:  121Gi total, 87Gi used, 31Gi free
# After killing LM Studio:   121Gi total, 4.8Gi used, 113Gi free
# → LM Studio was using ~82Gi
```

### GPU State
```bash
nvidia-smi
# GPU 0: NVIDIA GB10, Temp 44°C, Power 11W
# PID 35286: lmstudio node process using 82881 MiB (~81 GB)
```

### Crash Reports Found
```bash
ls -lt /var/crash/
# _usr_lib_xorg_Xorg.0.crash  →  348 KB,  Signal: 6 (SIGABRT),  Timestamp matched crash
# _opt_wechat_wechat.1000.crash  →  58 MB
```

### Xorg.0.log (old, pre-crash)
```bash
cat /var/log/Xorg.0.log.old | grep -iE "EE|fatal"
# → "Fatal server error: no screens found"  (from GPU driver initialization failure)
```

### Kernel Logs (current boot, no errors — clean start after crash)
```bash
cat /var/log/kern.log
# PCIe AER: "Correctable error" (Physical Layer) — minor, not crash cause
# Watchdog: "Hard watchdog permanently disabled"
# NVRM: "loading NVIDIA UNIX Open Kernel Module for aarch64 580.142"
```

## Backend Detection (Critical for GB10)

The #1 "it worked before reinstall" fix: check which llama.cpp backend LM Studio is using.

```bash
# List installed backends
ls ~/.lmstudio/extensions/backends/
# Expected: llama.cpp-linux-arm64-2.20.1 (CPU), llama.cpp-linux-arm64-nvidia-cuda13-2.20.1, llama.cpp-linux-arm64-nvidia-cuda13-2.22.0

# Current preference
cat ~/.lmstudio/.internal/backend-preferences-v1.json
# CPU: {"name": "llama.cpp-linux-arm64", "version": "2.20.1"}
# CUDA: {"name": "llama.cpp-linux-arm64-nvidia-cuda13", "version": "2.22.0"}

# GPU survey results
python3 -c "
import json, sys
with open('$HOME/.lmstudio/.internal/internal-engine-index.json') as f:
    data = json.load(f)['json']
for e in data:
    m = e['manifest']; s = e['hardwareSurveyResult']['gpuSurveyResult']
    print(f'{m[\"name\"]} v{m[\"version\"]}: GPU survey={s[\"result\"][\"code\"]}')
"
# CPU backend → "GPU survey=NoDevicesFound"
# CUDA backend → "GPU survey=Success"
```

### Switch to CPU Backend (for models >40GB)
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

### Switch to CUDA Backend (for models <=40GB)
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

## Critical LM Studio Log Entries

All from `~/.lmstudio/server-logs/2026-06/2026-06-25.1.log`:

### Successful Inference (before crash)
```
15:01:43  → POST /v1/chat/completions to nvidia/nemotron-3-super
           → Prompt: 18 tokens, eval 30 tokens
           → Timing: 54.22 tok/s prompt, 20.77 tok/s eval
           → WORKED — model loaded and served correctly
```

### Fatal Load Attempt with 64K Context
```
15:06:43  → POST /api/v1/models/load with body { "model": "nvidia/nemotron-3-super", "context_length": 64000 }
15:06:44  → LlamaV4::load config: n_parallel=4 n_ctx=64000 kv_unified=true
           → mlock FAILED: "Cannot allocate memory"
15:10:01  → "Model load request cancelled by client disconnect"
           → Load attempt took ~4 minutes before timeout
```

### Repeat Crash Loop (after failed load, system kept trying)
```
16:23:11  → Server restarted (LM Studio reopened)
16:23:39  → LlamaV4::load n_ctx=8192 kv_unified=true  (this time with 8K context)
           → Model loaded successfully
16:28:01  → POST /api/v1/models/load with context_length=64000  (AGAIN!)
           → Another failed 64K load attempt
16:36:33  → Server restarted again
16:36:36  → LlamaV4::load n_ctx=8192
16:55     → Xorg SIGABRT crash → system freeze/reboot
```

### Qwen3.5-35B-A3B Successful Inference (for comparison)
```
15:01:45  → POST /v1/chat/completions to qwen/qwen3.5-35b-a3b
           → Prompt: 11 tokens, eval 30 tokens
           → Timing: 37.82 tok/s prompt, 75.89 tok/s eval
           → NO memory issues, much faster
```

## Configuration Files Modified

### `/home/bobobears/.lmstudio/settings.json`
```json
{
  "defaultContextLength": { "type": "custom", "value": 4096 },
  "modelLoadingGuardrails": { "mode": "high", "customThresholdBytes": 4294967296, "alwaysAllowLoadAnyway": false },
  "enableLocalService": true
}
```

### `/home/bobobears/.lmstudio/.internal/http-server-config.json`
```json
{
  "autoStartOnLaunch": true,
  "port": 1234,
  "networkInterface": "0.0.0.0",
  "justInTimeModelLoading": false,
  "fileLoggingMode": "succinct"
}
```

### `/home/bobobears/.hermes/config.yaml` (Hermes side)
```yaml
model:
  default: nvidia/nemotron-3-super
  provider: lmstudio
  base_url: http://127.0.0.1:1234/v1
```

### `/etc/security/limits.conf` (memlock fix)
```
* soft memlock unlimited
* hard memlock unlimited
```
