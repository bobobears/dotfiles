# Truncated Zip Extraction — Partial GitHub Archive Recovery

When downloading GitHub archive zips from China, connections often time out
before the full file arrives. GitHub archives use **store (no compression)**
mode, so partial data is recoverable — the central directory at the end is
missing, but local file headers are intact.

## Diagnosis

```bash
# Check if file is truncated
file archive.zip
# → "Zip archive data, at least v1.0 to extract, compression method=store"
#   (NOT "Zip archive data, requires at least v2.0 to extract" — that's proper)

unzip -t archive.zip
# → "End-of-central-directory signature not found" → truncated
```

A truncated "store" zip is recoverable. A truncated "deflate" zip is not.

## Manual Extraction

GitHub archives store files sequentially with `PK\x03\x04` local file headers.
The last file may be cut off, but everything before it is intact.

### Python extractor

```python
import struct, os

zip_path = '/path/to/partial.zip'
dst = '/path/to/extract'

with open(zip_path, 'rb') as f:
    data = f.read()

extracted = 0
offset = 0

while True:
    idx = data.find(b'PK\x03\x04', offset)
    if idx < 0:
        break

    fname_len = struct.unpack('<H', data[idx+26:idx+28])[0]
    extra_len = struct.unpack('<H', data[idx+28:idx+30])[0]

    if idx + 30 + fname_len + extra_len > len(data):
        break

    fname = data[idx+30:idx+30+fname_len].decode('utf-8', errors='replace')
    data_start = idx + 30 + fname_len + extra_len
    next_idx = data.find(b'PK\x03\x04', data_start)

    file_data = data[data_start:next_idx] if next_idx > 0 else data[data_start:]
    local_path = os.path.join(dst, fname)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    with open(local_path, 'wb') as f:
        f.write(file_data)
    extracted += 1
    offset = idx + 1

print(f"Extracted {extracted} files")
```

### Limitations

- **Alphabetical cutoff**: GitHub archives list files alphabetically in
  directories. A truncated zip will have early-alphabet files (`.claude/`,
  `api/`, `apps/`) but may miss later-alphabet ones (`main.py`, `src/`,
  `requirements.txt`), even in the same directory.
- **Central directory gone**: `unzip`/`ZipFile` refuse to open truncated zips.
  The manual method above is required.
- **Size estimate**: A 58MB partial of an 85MB total (~68%) typically recovers
  ~415 of ~924 files (45%), covering subdirectories but missing root-level
  files and later-alphabet directories.

## Completing the Recovery

After extracting what the truncated zip provides, fill gaps with:

### 1. GitHub API (individual small files, unauthenticated: 60/hr)

```bash
curl -s "https://api.github.com/repos/owner/repo/contents/path/to/file" \
  -H "Accept: application/vnd.github.v3+json" \
  -H "User-Agent: agent"
# Response includes base64-encoded content
```

Best for: small files (<200KB), directory listings.

### 2. ghproxy.net for raw.githubusercontent.com

```bash
curl -sL "https://ghproxy.net/https://raw.githubusercontent.com/owner/repo/branch/path/file" \
  -o /tmp/file
```

Best for: any file size, can be slow but reliable. Use as a fallback when
direct raw.githubusercontent.com DNS resolves to 0.0.0.0.

### 3. aria2c multi-threaded (full archive re-download)

```bash
aria2c -x 4 -s 4 --connect-timeout=30 --timeout=600 \
  "https://github.com/owner/repo/archive/refs/heads/branch.zip" \
  -o repo.zip
```

Best for: completing the full download when speed is acceptable (20-50 KiB/s
→ 30-60 min for 85MB). **`--continue=true` rarely works** on GitHub because
redirect URLs use expiring signed tokens — start fresh.

### 4. pip install from git+https (for Python packages)

```bash
pip install "git+https://github.com/owner/repo.git"
```

Best for: installable Python packages (has pyproject.toml / setup.py).
May work when direct wget/curl fail because pip uses its own transport.

## Post-Extraction Recovery: The Iterative Dependency Chase

After extracting a truncated zip, many files are missing. When starting a
Python application, you'll hit a cascade of `ModuleNotFoundError` — one per
start attempt. This is normal.

### The Pattern

```
1. Extract partial zip → get ~45% of files
2. python server.py → ModuleNotFoundError: 'mod.x'
3. ghproxy download mod/x.py
4. python server.py → ModuleNotFoundError: 'mod.y'
5. Repeat 3-4 until server starts
```

Each iteration takes ~30-60s via ghproxy. Expect **8-15 rounds** for a
project with 200+ Python files (~85MB repo).

### Batch Download (faster than one-at-a-time)

Use a script to download all missing files in one pass from the repo tree JSON:

```python
# Requires /tmp/repo_tree.json (fetched from GitHub API)
import json, subprocess, os

with open('/tmp/repo_tree.json') as f:
    tree = json.load(f)

missing = [item['path'] for item in tree['tree']
           if item['type'] == 'blob' and item['path'].endswith('.py')
           and not os.path.exists(f'/dst/{item["path"]}')]

for path in missing:
    os.makedirs(os.path.dirname(f'/dst/{path}'), exist_ok=True)
    subprocess.run(['curl', '-sL',
        f'https://ghproxy.net/https://raw.githubusercontent.com/owner/repo/main/{path}',
        '-o', f'/dst/{path}'], timeout=45)

print(f'Downloaded {len(missing)} files')
```

**Tool-call limits**: `execute_code` is capped at 50 tool calls per invocation.
For repos with many missing files, run multiple rounds.

### Null Bytes from Truncated Extraction

Files from a truncated zip may contain **null bytes (`\x00`)** at the end
(zip entry padding). These cause `SyntaxError: source code string cannot
contain null bytes`.

```bash
# Scan for corrupted files
python3 -c "
import os
for root, dirs, files in os.walk('.'):
    if 'venv' in root: continue
    for f in files:
        if not f.endswith('.py'): continue
        with open(os.path.join(root, f), 'rb') as fh:
            data = fh.read()
        if b'\x00' in data:
            print(f'CORRUPTED: {os.path.join(root, f)}')
"

# Fix: re-download each corrupted file via ghproxy
# curl -sL 'https://ghproxy.net/https://raw.githubusercontent.com/owner/repo/main/path' -o path
```

**Prevention**: Scan for null bytes before first run and re-download all
corrupted files. This eliminates one class of errors from the chase.

### GitHub API Rate Limit Reset

The unauthenticated GitHub API allows 60 requests/hour. When rate-limited:

```json
{"message": "API rate limit exceeded..."
```

Options:
1. Wait for the hourly window to reset (check `X-RateLimit-Reset` header)
2. Use ghproxy raw URLs instead (no rate limit, just slower per-file)
3. Authenticate: pass a GitHub token via `Authorization: Bearer <token>`
   header for 5000 req/hour

## Strategy Summary

| Approach | Speed | Reliable | Best For |
|----------|-------|----------|----------|
| aria2c multi-threaded | ~25 KB/s | ⚠️ times out often | Full archive |
| ghproxy raw URL | ~3-5s/file | ✅ | Individual missing files |
| GitHub API (unauth) | Instant | ⚠️ 60/hr limit | Directory listing, small files |
| Partial zip extraction | Fast | ✅ partial | Getting most files quickly |
| Dependency chase | ~30-60s/round | ✅ | Fixing remaining imports |
