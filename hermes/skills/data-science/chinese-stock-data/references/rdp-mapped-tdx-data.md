# RDP-Mapped Drive: TDX Stock Data via thinclient_drives

## Context
Stock data residing on a Windows partition or remote machine exposed to Linux via RDP's `thinclient_drives/` fuse mount (xrdp-chansrv). Shell commands like `ls`, `find`, `grep` time out on large directories because the fuse mount is slow — use Python `execute_code` instead.

## Typical Path Structure
```
/home/bobobears/thinclient_drives/E:/<tdx-installation>/vipdoc/<exchange>/lday/<code>.day
```

Common TDX installation folder names on the E: drive:
- `华安证券通达信版/` — may have older data (data ends ~2024)
- `zd_hazq/` — may also be outdated
- `zd_hazq_gm/` — typically has the most current data

## Step-by-Step Workflow

### 1. Locate the file
```python
import os

paths_to_try = [
    "/home/bobobears/thinclient_drives/E:/zd_hazq_gm/vipdoc/sz/lday/sz002966.day",
    "/home/bobobears/thinclient_drives/E:/zd_hazq/vipdoc/sz/lday/sz002966.day",
    "/home/bobobears/thinclient_drives/E:/华安证券通达信版/vipdoc/sz/lday/sz002966.day",
]
file_path = next((p for p in paths_to_try if os.path.exists(p)), None)
```

### 2. Determine price scaling (×100 vs ×1000)
Use the `amount` field cross-check — see SKILL.md's "Determine scaling before parsing" section for the algorithm.

In this environment (`zd_hazq_gm`): scale = **×100** (price = int / 100).
Example: `open=771` → `7.71 元`, `close=767` → `7.67 元`.

### 3. Parse target date
```python
import struct

record_size = 32
target_date = 20260622  # YYYYMMDD

with open(file_path, "rb") as f:
    data = f.read()

num_records = len(data) // record_size
for i in range(num_records):
    offset = i * record_size
    rec = data[offset:offset + record_size]
    date_val, open_p, high_p, low_p, close_p, amount, volume, reserved = \
        struct.unpack("<iiiiifii", rec)
    
    if date_val == target_date:
        year, month, day = date_val // 10000, (date_val % 10000) // 100, date_val % 100
        print(f"开盘: {open_p/100:.3f}  最高: {high_p/100:.3f}")
        print(f"最低: {low_p/100:.3f}  收盘: {close_p/100:.3f}")
        print(f"成交额: {amount:,.2f}  成交量: {volume:,} 股 ({volume/100:,.0f} 手)")
        break
```

### 4. Check previous trading day for comparison
```python
if i > 0:
    prev_rec = data[(i-1)*32:(i-1)*32+32]
    prev_date, _, _, _, prev_close, _, _, _ = struct.unpack("<iiiiifii", prev_rec)
    change_pct = (close_p - prev_close) / prev_close * 100
    print(f"较前日: {change_pct:+.2f}% (前收: {prev_close/100:.3f})")
```

## DNS / Internet Access Note
When running inside the Hermes desktop app, the system DNS (systemd-resolved via 127.0.0.53 to router 192.168.31.1) may REFUSE external lookups. Workaround: use `nslookup domain 223.5.5.5` to get the IP from Alibaba DNS, then use `curl --resolve "host:443:ip" URL` to bypass the broken resolver.
