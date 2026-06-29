# Truncated ZIP Recovery from Partial GitHub Downloads

When downloading large GitHub archive repos from China (~30KB/s), the ZIP often gets truncated before the central directory is written. Standard `unzip` fails with "cannot find zipfile directory".

## Recovery via PK Header Scanning

GitHub archives use **store** (no compression) method. Each file is stored sequentially with a `PK\x03\x04` local file header. Extract usable files with Python:

```python
import struct, os

zip_path = 'repo.zip'
dst = 'extracted/'

with open(zip_path, 'rb') as f:
    data = f.read()

extracted = 0
offset = 0

while True:
    idx = data.find(b'PK\x03\x04', offset)
    if idx < 0:
        break
    
    # Parse local file header
    fname_len = struct.unpack('<H', data[idx+26:idx+28])[0]
    extra_len = struct.unpack('<H', data[idx+28:idx+30])[0]
    
    if idx + 30 + fname_len + extra_len > len(data):
        break
    
    fname = data[idx+30:idx+30+fname_len].decode('utf-8', errors='replace')
    
    # Data starts after header + filename + extra
    data_start = idx + 30 + fname_len + extra_len
    
    # Find next file to determine this file's data boundaries
    next_idx = data.find(b'PK\x03\x04', data_start)
    file_data = data[data_start:next_idx] if next_idx > 0 else data[data_start:]
    
    # Save
    local_path = os.path.join(dst, fname)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    with open(local_path, 'wb') as f:
        f.write(file_data)
    extracted += 1
    
    offset = idx + 1

print(f"Extracted {extracted} files")
```

## Post-Extraction Cleanup

Files from partial extraction may have trailing null bytes. Fix:

```bash
# Find and re-download corrupted .py files
python3 -c "
import os
for root, dirs, files in os.walk('.'):
    for f in files:
        if not f.endswith('.py'): continue
        path = os.path.join(root, f)
        with open(path, 'rb') as fh:
            if b'\\x00' in fh.read():
                print(f'NULL BYTES: {path}')
"

# Re-download via ghproxy proxy:
curl -sL "https://ghproxy.net/https://raw.githubusercontent.com/owner/repo/main/{path}" -o "{path}"
```
