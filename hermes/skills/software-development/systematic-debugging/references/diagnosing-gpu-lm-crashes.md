# Diagnosing GPU/System Crashes from Local LLM Inference

## When to Use

When a user reports their **system freezes, crashes, or reboots** while running local LLM inference — especially on unified-memory platforms (NVIDIA GB10/Project DIGITS, Apple Silicon, Grace Hopper) where CPU and GPU share the same physical RAM pool.

## Key Diagnostic Principle

**On unified-memory platforms, running out of memory does NOT produce a clean CUDA OOM error. It causes the entire SoC to become unstable — Xorg crashes (SIGABRT), kernel hangs, unexpected system reboots.** This is the single most important distinction from discrete-GPU systems (RTX/A100/H100).

## Platform Identification

```bash
# Check for GB10 / Grace Blackwell
cat /proc/cpuinfo | grep -i "cpu part"     # 0xd0d = Grace ARM
uname -m                                     # aarch64 = ARM
nvidia-smi | grep -i "GB10\|Grace\|DGX"    # DGX Spark / Project DIGITS

# Check if unified memory architecture
cat /proc/meminfo | grep MemTotal            # Usually 121-128GB on GB10
# Unified memory: nvidia-smi shows memory but NOT as separate VRAM
nvidia-smi                                   # "Not Supported" for memory means unified
```

## Initial Triage Commands (Phase 1)

Run these immediately — they are NOT blocked by system-crash guards:

```bash
# 1. Free memory — the key metric
free -h
cat /proc/meminfo | grep -E "MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree"

# 2. GPU state + memory usage
nvidia-smi
# On unified memory: check which process, how much it consumed

# 3. GPU temperature
nvidia-smi -q -d TEMPERATURE

# 4. System temperatures
sensors

# 5. Uptime — confirms recent crash/reboot
uptime

# 6. Crash report directory
ls -lt /var/crash/

# 7. Current kernel log (from fresh boot after crash)
cat /var/log/kern.log | grep -iE "oom|out of memory|kill|panic|error|reset|hung|nvidia|fatal" | tail -40

# 8. Xorg crash reports
ls -lt /var/log/Xorg*

# 9. Old Xorg log (from before crash)
cat /var/log/Xorg.0.log.old | grep -iE "error|fatal|EE|segfault|abort"

# 10. LM Studio server logs
cat ~/.lmstudio/server-logs/$(date +%Y-%m)/$(date +%Y-%m-%d)*.log | head -200
```

## Critical Crash Signatures & Their Meanings

### Signal: SIGABRT (Signal 6) in Xorg
```
ProblemType: Crash  |  Signal: 6  |  SignalName: SIGABRT
```
**Meaning:** Xorg server hit an assertion failure, likely triggered by NVIDIA driver memory allocation failure or GPU context corruption under memory pressure. This is the **proximate cause** of "screen freeze / black screen."

### mlock failure in llama.cpp
```
warning: failed to mlock 301989888-byte buffer: Cannot allocate memory
```
**Meaning:** The system cannot lock memory pages — immediate sign of memory pressure on unified memory. Often precedes the crash by seconds to minutes.

### Just-in-time model load cancelled
```
Model load request cancelled by client disconnect
```
**Meaning:** The load attempt took too long (3+ minutes) because memory was exhausted. The client timed out, but the model load process still consumed memory and may trigger the crash.

### PCIe AER Correctable Errors
```
PCIe Bus Error: severity=Correctable, type=Physical Layer, (Receiver ID)
```
**Meaning:** Signal integrity issues on PCIe. Usually benign alone, but combined with heavy GPU memory load they indicate power delivery or interconnect instability.

## Memory Budget Calculation for Unified Memory

Use this formula when diagnosing:

```
Total unified memory  = MemTotal from /proc/meminfo
  
When running model X at quantization Q:
  Model weights     ≈ total_gguf_file_size × 0.85 (roughly, weight data in GGUF)
  KV cache          = context_length × n_gqa_groups × n_layers × 2 bytes × 2 (K+V)
  Prompt cache      = as configured in LM Studio (often 8 GiB = 8192 MiB)
  Overhead          = Electron/LLM runtime (~3-5 GB)
  OS + desktop      = ~3-5 GB

Budget check: weights + KV_cache + prompt_cache + overhead + OS < MemTotal
```

### Real-World Example: GB10 (121 GB usable)

| Model | Quant | Est. Weights | Feasible? |
|-------|-------|-------------|-----------|
| Nemotron-120B-A12B | Q4_K_M | ~68 GB | Marginal (with 8K ctx OK, with 64K ctx → crash) |
| Nemotron-120B-A12B | Q3_K_M | ~51 GB | Likely OK |
| Qwen3.5-35B-A3B | Q4_K_M | ~20 GB | Comfortable (76 tok/s observed) |
| Llama-3.1-70B | Q4_K_M | ~39 GB | Feasible with 8K ctx |

## LM Studio Specific Checks

```bash
# Check loaded model from LM Studio logs
grep "LlamaV4::load called" ~/.lmstudio/server-logs/*/*.log

# Check context length configuration
grep "n_ctx=" ~/.lmstudio/server-logs/*/*.log

# Check JIT model loading setting (changed via LM Studio UI)
cat ~/.lmstudio/.internal/http-server-config.json | grep justInTimeModelLoading

# Check model files on disk
find ~/.lmstudio/models -name "*.gguf" -exec ls -lh {} \;
du -sh ~/.lmstudio/models/
```

## Common Root Causes (Ranked by Likelihood)

1. **Model size exceeds available unified memory headroom**
   - Most common cause on GB10/Apple Silicon
   - Fix: switch to smaller model or lighter quantization

2. **Context length set too high**
   - KV cache grows linearly with context length
   - Fix: reduce context_length to 4096-8192

3. **Prompt cache enabled**
   - LM Studio allocates ~8 GB for prompt cache by default
   - Fix: disable in LM Studio settings or set `--cache-ram 0`

4. **Multiple concurrent slots**
   - Each slot has its own KV cache
   - Fix: reduce `n_parallel` in LM Studio (default is 4)

5. **mlock / memlock limits too low**
   - llama.cpp tries to lock pages for performance
   - Fix: `sudo bash -c 'echo "* - memlock unlimited" >> /etc/security/limits.conf'`

## Prevention Checklist

- [ ] Calculate memory budget before loading a new model
- [ ] Keep context_length at 4096-8192 for large models on unified memory
- [ ] Disable prompt cache when memory is tight
- [ ] Reduce n_parallel (slots) for large models
- [ ] Set `kernel.panic=30` to enable clean reboot instead of freeze
- [ ] Monitor with `watch -n 5 nvidia-smi` during first inference
- [ ] Test with a lightweight model first to verify system stability

## What NOT to Do

- Do NOT assume this is a hardware fault — it is almost always memory budgeting
- Do NOT try to fix by reinstalling drivers or swapping hardware
- Do NOT report "Xorg bug" upstream — Xorg is the victim, not the cause
- Do NOT set swap on unified memory systems — swapping unified memory crashes the system
