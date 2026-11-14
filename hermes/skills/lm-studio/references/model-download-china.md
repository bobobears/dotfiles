# Large GGUF Model Download from China Network

## Problem

- HuggingFace is slow or DNS-blocked from China
- `hf download` (the modern CLI) can timeout on files >5GB — it uses single-stream HTTP
- LM Studio's built-in download is also slow (no multi-thread)
- Need to download single large GGUF files (5-130 GB) directly into LM Studio's model directory

## Solution: aria2c on hf-mirror.com

Use `aria2c` with 4 parallel connections on `hf-mirror.com` (the official HF mirror). aria2c:
- Supports multi-threaded download (4-16 concurrent connections)
- Resumes interrupted downloads automatically (`--continue=true`)
- Handles 302 redirects to CDN (the Xet/CAS bridge that hf-mirror uses)
- Can run in background while you do other work

## Step-by-Step

### 1. Discover the model and find the exact GGUF filename

```bash
export HF_ENDPOINT=https://hf-mirror.com

# Check what files are available (dry run)
hf download <user>/<model> --dry-run
# Output shows every file and its size, e.g.:
#   Qwen3.5-35B-A3B-Q8_0.gguf  36.9G

# Or check the repo directly
curl -sL "https://hf-mirror.com/<user>/<model>/tree/main" | grep -oP 'href="[^"]+\.gguf"' | head -5
```

### 2. Download directly into LM Studio's model directory

```bash
cd ~/.lmstudio/models/<user>/<model>/

aria2c -x 4 -s 4 --continue=true \
  --header="User-Agent: huggingface-hub/1.21.0" \
  -o "<filename.gguf>" \
  "https://hf-mirror.com/<user>/<model>/resolve/main/<filename.gguf>"
```

**Parameters explained:**
- `-x 4` — max 4 connections per server (good balance of speed vs server load)
- `-s 4` — split file into 4 segments (parallel download)
- `--continue=true` — resume if interrupted (safe to Ctrl+C and restart)
- `--header="User-Agent: ..."` — hf-mirror.com requires a browser-like User-Agent
- `-o <filename>` — output filename (keeps original name)

### 3. Run in background (recommended for large files)

```bash
cd ~/.lmstudio/models/<user>/<model>/
aria2c -x 4 -s 4 --continue=true \
  --console-log-level=error \
  --summary-interval=60 \
  --header="User-Agent: huggingface-hub/1.21.0" \
  -o "<filename.gguf>" \
  "https://hf-mirror.com/<user>/<model>/resolve/main/<filename.gguf>" &

# Track progress manually
watch 'ls -lh ~/.lmstudio/models/<user>/<model>/<filename.gguf>'
```

### 4. Set up automated completion check (in Hermes TUI)

When speed is ~10-20 MiB/s and the file is ~35 GB, expect 30-60 minutes. Use a cron job that checks every 5 minutes:

```bash
# Check periodically:
ls -lh ~/.lmstudio/models/<user>/<model>/<filename.gguf>
# When size matches expected (e.g., 36.9 GB for Q8_0 of 35B model)
# and no aria2c process, it's done.
```

Or in Hermes, create a cronjob to check:
```bash
hermes cron create --schedule "5m" --repeat 12 \
  --prompt "Check if <filename> has finished downloading at ~/.lmstudio/models/<user>/<model>/" \
  --deliver origin
```

### 5. Verify the download

After completion, verify the file is a valid GGUF:

```bash
# Check magic bytes (GGUF files start with 'GGUF' at offset 0)
head -c 4 ~/.lmstudio/models/<user>/<model>/<filename.gguf> | xxd

# Expected: 00000000: 4747 5546 ... = "GGUF"

# Deeper header verification (tensor count, architecture name)
python3 -c "
import struct
with open('<filename.gguf>', 'rb') as f:
    magic = struct.unpack('<I', f.read(4))[0]
    assert magic == 0x46554747, f'Bad magic: 0x{magic:08X}'
    version = struct.unpack('<I', f.read(4))[0]
    tensor_count = struct.unpack('<Q', f.read(8))[0]
    metadata_len = struct.unpack('<Q', f.read(8))[0]
    f.seek(16 + metadata_len)
    print(f'GGUF v{version}, {tensor_count} tensors')
    f.seek(0, 2)
    print(f'File size: {f.tell()} bytes ({f.tell()/1024**3:.2f} GB)')
"

# Check file size matches expected
ls -lh ~/.lmstudio/models/<user>/<model>/<filename.gguf>

# Verify with LM Studio's native API (after loading)
curl -s http://127.0.0.1:1234/api/v1/models | python3 -m json.tool | grep "<model-name>"
```

### 6. Use in LM Studio

The model file is already in `~/.lmstudio/models/<user>/<model>/`. LM Studio will auto-discover it on next launch or model list refresh. No additional steps needed.

## Real-World Example: Qwen3.5-35B-A3B Q8_0

```bash
export HF_ENDPOINT=https://hf-mirror.com

cd ~/.lmstudio/models/lmstudio-community/Qwen3.5-35B-A3B-GGUF/

aria2c -x 4 -s 4 --continue=true \
  --header="User-Agent: huggingface-hub/1.21.0" \
  -o "Qwen3.5-35B-A3B-Q8_0.gguf" \
  "https://hf-mirror.com/lmstudio-community/Qwen3.5-35B-A3B-GGUF/resolve/main/Qwen3.5-35B-A3B-Q8_0.gguf"
```
- Expected size: 34.37 GiB (36,903,139,136 bytes)
- Speed: 10-22 MiB/s on a typical home connection in China
- ETA: ~25-45 minutes at that speed

## Pitfalls

- **hf CLI (`hf download`) times out on large files** (>5GB) because it's single-stream. Always use aria2c for files >5GB.
- **hf CLI is deprecated** — the old `huggingface-cli download` no longer works. Use `hf` or aria2c.
- **The redirect URL expires** — hf-mirror.com returns a 1-hour signed S3/Xet URL. aria2c handles this automatically but if the download stalls >1 hour, kill it and restart (aria2c's `--continue` resumes from where it left off).
- **File size may read as 35G early** — the `ls` command shows partial allocation. Wait until aria2c finishes and the size stops growing.
- **Speed fluctuations are normal** — expect 0.5-20 MiB/s variations. The average over the full download will be lower than peak speed. Don't restart just because speed dipped.

### aria2c Hang: Completed Download But Process Still Running

**Symptom:** aria2c is still running (`ps aux | grep aria2c` shows it), but:
- The file size matches the server's Content-Length
- `ls -l --time-style=full-iso` shows mtime still updating (from `.aria2` control file writes, not data writes)
- `ss -tnp | grep aria2c` shows ESTABLISHED sockets with Send-Q=0 (nothing in transit)
- `.aria2` control file (e.g. `filename.gguf.aria2`) is present alongside the .gguf
- No data transfer for 30+ seconds across multiple checks

**Root cause:** hf-mirror.com serves files via Xet/CAS (content-addressable storage bridge). The file itself is fully downloaded to disk (Content-Length matches), but aria2c gets stuck in a connection cleanup state — it followed the 302 redirect to the CloudFront CDN, finished receiving all data, but never exited cleanly. This is specific to the Xet/CAS redirect chain; aria2c from direct links usually exits normally.

**How to detect reliably:**

```bash
# 1. Get the true expected size from the server
#    The HEAD request follows redirects and returns the final Content-Length
curl -sI -L --max-time 15 \
  "https://hf-mirror.com/<user>/<model>/resolve/main/<filename.gguf>" \
  2>&1 | grep -i "Content-Length"

# 2. Compare with local file size
stat --format='%s' ~/.lmstudio/models/<user>/<model>/<filename.gguf>

# 3. Check for .aria2 control file (indicates aria2c hasn't finalized)
ls -la ~/.lmstudio/models/<user>/<model>/<filename.gguf>.aria2

# 4. Check process state
ps aux | grep aria2c | grep -v grep
ss -tnp | grep aria2c   # look for send-Q=0 on all connections
```

**How to verify GGUF integrity independently of aria2c:**

The file on disk is complete even though aria2c hasn't exited. Validate directly:

```bash
# GGUF magic bytes at offset 0 should be readable
head -c 4 <path> | xxd
# Expected: "4747 5546" = ASCII "GGUF"

# Full header parse
python3 -c "
import struct
with open('<filename.gguf>', 'rb') as f:
    magic = struct.unpack('<I', f.read(4))[0]
    assert magic == 0x46554747, f'Bad magic: 0x{magic:08X}'
    version = struct.unpack('<I', f.read(4))[0]
    tensor_count = struct.unpack('<Q', f.read(8))[0]
    metadata_len = struct.unpack('<Q', f.read(8))[0]
    f.seek(16 + metadata_len)
    print(f'GGUF v{version}, {tensor_count} tensors')
    f.seek(0, 2)
    actual_size = f.tell()
    print(f'File size: {actual_size} bytes ({actual_size/1024**3:.2f} GB)')
"
```

**How to safely clean up the stuck aria2c:**

```bash
# 1. Confirm file size matches server Content-Length (from HEAD request above)
# 2. Kill the hung process
kill <aria2c_pid>
# 3. Confirm no aria2c processes remain
ps aux | grep aria2c | grep -v grep || echo "clean"
# 4. Remove the stale .aria2 control file
rm -f <filename.gguf>.aria2
```

After cleanup, the .gguf is ready to use — no re-download needed. The file is intact.

### Non-Standard Formats (BF16, F16, F32)

Some model repos provide **BF16** (Bfloat16) or **F16/F32** base formats instead of standard K-quants. These are larger but lossless. Key differences:

- **BF16 files** are valid GGUF format and load in llama-server without issues
- **File sizes** are larger than K-quants (e.g. Qwythos-9B BF16 = 17.1 GB vs Q4_K_M ≈ 5.5 GB)
- **Performance** on the DGX Spark: BF16 9B model runs at ~13 tok/s with CUDA13 backend
- **Raw token output** may appear garbled in initial responses — the BF16 format produces valid output, but the model's raw output layer emits unprocessed logits that llama.cpp's tokenizer handles normally; any garbled-looking output is the response itself, not corruption
- **llama-server** handles BF16 correctly with `--flash-attn auto`
- **Multi-modal projector** (mmproj) files are needed alongside the GGUF for vision models

When downloading BF16 files:
```bash
# size is ~17 GB for a 9B model — verify after download
ls -lh <filename.gguf>

# Also download mmproj companion (if available)
aria2c -x 4 -s 4 --continue=true \
  --header="User-Agent: huggingface-hub/1.21.0" \
  -o "mmproj-<model>-f16.gguf" \
  "https://hf-mirror.com/<user>/<model>/resolve/main/mmproj-<model>-f16.gguf"
```



| Signal | Action |
|--------|--------|
| File growing, mtime changing, send-Q > 0 | Wait — actively downloading |
| File static, mtime changing (from .aria2 writes), send-Q = 0 for 30+ sec | Kill — aria2c is hung after completion |
| File matches server Content-Length exactly | Safe to kill — file is complete |
| No .aria2 file present, no aria2c process | Download is naturally complete, no action needed |

## Alternative: Background via terminal() in Hermes

```bash
# In terminal(background=true, notify_on_complete=true)
cd ~/.lmstudio/models/<user>/<model>/
aria2c -x 4 -s 4 --continue=true \
  --console-log-level=error \
  --summary-interval=60 \
  --header="User-Agent: huggingface-hub/1.21.0" \
  -o "<filename.gguf>" \
  "https://hf-mirror.com/<user>/<model>/resolve/main/<filename.gguf>"
```

Then use `process(action="poll")` or `process(action="wait")` to track. Note: background mode with aria2c's `--summary-interval` produces periodic progress output.
