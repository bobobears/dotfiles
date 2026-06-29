# GGUF Download Verification & LM Studio Integration

## Workflow: Download → Verify → Integrate → Test

A complete end-to-end workflow for downloading large GGUF models via aria2c from hf-mirror.com,
verifying integrity, placing them in LM Studio's directory structure, and testing via llama-server.

## Step 1: Discover & Download

Use aria2c with 4+ parallel connections. See `references/model-download-china.md` for details.

```bash
mkdir -p ~/.lmstudio/models/<hf-org>/<model>/
cd ~/.lmstudio/models/<hf-org>/<model>/

aria2c -x 4 -s 4 --continue=true \
  --header="User-Agent: huggingface-hub/1.21.0" \
  -o "<filename.gguf>" \
  "https://hf-mirror.com/<hf-org>/<model>/resolve/main/<filename.gguf>"
```

If the model has a **multimodal projector** (mmproj), download that too:
```bash
aria2c -x 4 -s 4 --continue=true \
  --header="User-Agent: huggingface-hub/1.21.0" \
  -o "mmproj-<model>-f16.gguf" \
  "https://hf-mirror.com/<hf-org>/<model>/resolve/main/mmproj-<model>-f16.gguf"
```

## Step 2: Verify GGUF Integrity

After aria2c completes (or if it appears stuck — see the "aria2c hang" pitfall in model-download-china.md):

```bash
# Check magic bytes
head -c 4 <filename.gguf> | xxd
# Expected: 47475546 = "GGUF"

# Parse header
python3 -c "
import struct
with open('<filename.gguf>', 'rb') as f:
    magic = struct.unpack('<I', f.read(4))[0]
    assert magic == 0x46554747
    version = struct.unpack('<I', f.read(4))[0]
    n_tensors = struct.unpack('<Q', f.read(8))[0]
    n_kv = struct.unpack('<Q', f.read(8))[0]
    print(f'GGUF v{version}, {n_tensors} tensors, {n_kv} KV entries')
    # Read general.architecture
    for i in range(min(n_kv, 15)):
        k_len = struct.unpack('<Q', f.read(8))[0]
        key = f.read(k_len).decode('utf-8')
        v_type = struct.unpack('<I', f.read(4))[0]
        if key in ('general.architecture', 'general.name', 'general.file_type'):
            if v_type == 6:  # string
                s_len = struct.unpack('<Q', f.read(8))[0]
                val = f.read(s_len).decode('utf-8')
                print(f'  {key} = {val}')
            else:
                # skip non-string
                pass
        else:
            if v_type == 6:
                s_len = struct.unpack('<Q', f.read(8))[0]
                f.read(s_len)
    f.seek(0, 2)
    print(f'File size: {f.tell() / 1024**3:.1f} GB')
"
```

## Step 3: Integrate with LM Studio

### 3a: Get the Correct Directory Path

LM Studio expects models at `~/.lmstudio/models/<hf-org>/<model-name>/<filename.gguf>`.

**⚠️ LM Studio may mis-parent downloads.** Observed issue: when searching for one model (e.g. Qwen3.5) and downloading a different model (e.g. Qwythos), LM Studio places the file under `~/.lmstudio/models/<searched-model>/<actual-hf-org>/<actual-model>/`. This means the model ends up nested incorrectly, e.g.:
```
~/.lmstudio/models/lmstudio-community/Qwen3.5-35B-A3B-GGUF/   # searched model
  └── empero-ai/                                               # actual HF org
        └── Qwythos-9B-Claude-Mythos-5-1M-GGUF/                # actual model
              ├── Qwythos-9B-Claude-Mythos-5-1M-MTP-BF16.gguf
              └── mmproj-Qwythos-9B-Claude-Mythos-5-1M-f16.gguf
```

The correct path should be:
```
~/.lmstudio/models/empero-ai/Qwythos-9B-Claude-Mythos-5-1M-GGUF/
  ├── Qwythos-9B-Claude-Mythos-5-1M-MTP-BF16.gguf
  └── mmproj-Qwythos-9B-Claude-Mythos-5-1M-f16.gguf
```

### 3b: Fix with Hardlinks (Zero Extra Disk Space)

If aria2c downloaded to the correct `empero-ai/` directory but LM Studio's system put files in the wrong nested path, use hardlinks to share the file across both locations:

```bash
# 1. Create the correct target directory (if not exists)
mkdir -p ~/.lmstudio/models/empero-ai/Qwythos-9B-Claude-Mythos-5-1M-GGUF/

# 2. Hardlink the GGUF — same inode, zero extra disk
ln ~/.lmstudio/models/empero-ai/Qwythos-9B-Claude-Mythos-5-1M-GGUF/Qwythos-9B-Claude-Mythos-5-1M-MTP-BF16.gguf \
   ~/.lmstudio/models/lmstudio-community/Qwen3.5-35B-A3B-GGUF/empero-ai/Qwythos-9B-Claude-Mythos-5-1M-GGUF/

# 3. Hardlink the mmproj too (if one path has it and the other doesn't)
ln <source>/mmproj-*.gguf <target>/mmproj-*.gguf

# 4. Verify via inode number
stat --format='%i %n' <path1>/<file.gguf> <path2>/<file.gguf>
# Both should show the same inode number (same data on disk)
```

**Prerequisites:**
- Both directories must be on the **same filesystem** (`df -T .` — hardlinks don't cross filesystem boundaries)
- The target directory must already exist (created by LM Studio's download system)
- Soft links (symlinks) won't work; LM Studio resolves them before comparison

### 3c: Clear LM Studio Caches

After placing files, force LM Studio to rescan:

```bash
rm -f ~/.lmstudio/.internal/gguf-metadata-cache.json
rm -f ~/.lmstudio/.internal/model-index-cache.json
rm -f ~/.lmstudio/.internal/model-data.json
```

Then restart LM Studio or click "Refresh model list" if available.

## Step 4: Quick Verification via llama-server

Bypass LM Studio's UI entirely to confirm the model loads and runs:

```bash
# Find the llama-server binary bundled with LM Studio
find ~/.lmstudio/extensions/backends/ -name "llama-server" -type f 2>/dev/null

# Start on a unique port (not 1234 if LM Studio uses that)
LLAMA_SERVER=~/.lmstudio/extensions/backends/llama.cpp-linux-arm64-nvidia-cuda13-2.23.1/llama-server

$LLAMA_SERVER \
  --model "<absolute-path-to-gguf>" \
  --port 1237 \
  --n-gpu-layers 99 \
  --flash-attn auto
```

Wait for `"server is listening on http://127.0.0.1:1237"` in logs, then test:

```bash
# Test completions endpoint
curl -s -m 30 http://127.0.0.1:1237/v1/completions \
  -d '{"prompt": "Hello", "n_predict": 20}' | python3 -m json.tool

# Test chat completions
curl -s -m 60 http://127.0.0.1:1237/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "test",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Say hello in Chinese."}
    ],
    "max_tokens": 100,
    "temperature": 0.7
  }'
```

Expected response includes `choices[0].message.content` and shows the model name in the response.

### BF16 Model Format Note

Some models (like Qwythos) are in **BF16 format** (BFloat16), not standard K-quant. These produce valid GGUF output and load correctly, but the raw token output may appear garbled if the chat template expects specific formatting. This is normal — test with a simple prompt to confirm the engine is running.

## Step 5: Use in LM Studio

After the hardlink fix and cache clearing:
1. Restart LM Studio
2. The model should appear in the model list under the correct name
3. If it doesn't appear: see `references/model-variant-detection.md` for the three-tier model state debugging

If the model still doesn't appear in LM Studio's UI after all steps, **run it directly via llama-server** (Step 4) — this is fully functional and bypasses LM Studio's model management entirely. Configure Hermes to point at the llama-server port.

## Verification Checklist

- [ ] GGUF magic bytes = `47475546`
- [ ] File size matches expected (check README from HF repo)
- [ ] Header parse succeeds (tensor count, architecture key)
- [ ] Hardlinks share same inode (`stat --format='%i' <path1> <path2>`)
- [ ] llama-server starts and listens on port
- [ ] curl test returns valid chat completions response
- [ ] MMproj file present alongside GGUF (if model supports vision)
- [ ] LM Studio caches cleared (model-index-cache, gguf-metadata-cache, model-data)
