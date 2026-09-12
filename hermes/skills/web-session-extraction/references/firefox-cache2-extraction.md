# Firefox cache2 / history / session forensics recipes

All read-only, zero network requests. Profile path: `~/.config/mozilla/firefox/<profile>/`.

## 1. Extract loaded pages from cache2 (validated)

Entries: `<cache dir>/cache2/entries/*` — flat binary files, no on-disk index.
Structure: header region containing the request URL as plain text, then a gzip payload starting at `\x1f\x8b`.

```python
import os, re, glob, zlib

C = os.path.expanduser("~/.cache/mozilla/firefox/<profile>/cache2/entries")

def gunzip_scan(data):
    """Find and decompress all gzip streams in a cache entry."""
    out, i = [], 0
    while True:
        j = data.find(b"\x1f\x8b", i)
        if j < 0: break
        try:
            d = zlib.decompressobj(16 + zlib.MAX_WBITS)
            dec = d.decompress(data[j:])
            out.append(dec)
            i = len(data) - len(d.unused_data) if d.unused_data else len(data)
        except Exception:
            i = j + 2
    return out

# Map every cached URL for a target host (URL lives in the header region, first ~4KB):
site_urls = {}
for f in glob.glob(C + "/*"):
    data = open(f, "rb").read()
    if b"TARGET_HOST:PORT" not in data[:4000]:
        continue
    for m in re.findall(rb"https?://TARGET[^\x00-\x1f\"<> ]{0,160}", data[:4000]):
        streams = gunzip_scan(data)
        best = max(streams, key=len) if streams else b""
        site_urls.setdefault(m.decode(), []).append((len(best), os.path.basename(f)))
```

Notes:
- To verify a navigation actually happened: filter entries by `os.path.getmtime(f)` within the last few minutes, decompress, inspect. Telemetry entries (mozilla.org) show up — ignore them.
- Classify payload type from the first bytes of the decompressed stream before trusting keyword matches.

## 2. History (validated)

```python
import sqlite3, os, time
P = os.path.expanduser("~/.config/mozilla/firefox/<profile>")
con = sqlite3.connect(f"file:{P}/places.sqlite?immutable=1", uri=True)
rows = con.execute("""
    SELECT hv.visit_date/1000000.0, p.url
    FROM moz_historyvisits hv JOIN moz_places p ON hv.place_id=p.id
    WHERE p.url LIKE '%TARGET%' ORDER BY hv.visit_date DESC LIMIT 20""").fetchall()
```

- Table is `moz_historyvisits` (not `visits`). visit_date is µs since epoch → `/1000000.0`.
- **immutable=1 caveat**: reads a snapshot that excludes uncheckpointed WAL data — visits made seconds ago may be invisible. For fresh state, copy the DB + `-wal` and open normally (or use the sqlite3 backup API; it can block while Firefox holds locks — run with a timeout).

## 3. Cookies (validated)

```python
con = sqlite3.connect(f"file:{P}/cookies.sqlite?immutable=1", uri=True)
rows = con.execute("SELECT host, name FROM moz_cookies").fetchall()
hits = [r for r in rows if "TARGET_HOST" in (r[0] or "")]
```

Zero cookies for the target host while history shows a logged-in main page → session is memory-only (in-process). Never close that browser window.

## 4. Session store: recovery.jsonlz4 (validated)

Firefox-private `mozLz40` chunked format — NOT an LZ4 frame. Magic bytes: `6d6f7a4c7a343000` (`mozLz40\x00`).
Parse: after the 8-byte magic, repeated chunks of [8-byte header][compressed block]; decompress each block with `lz4.block.decompress(block, uncompressed_size_from_header)`, concatenate → JSON containing open tabs (url + title).

## 5. Screenshot pipeline (only when vision is available)

`DISPLAY=:10 XAUTHORITY=~/.Xauthority xwd -root -silent > f.xwd && ffmpeg -y -i f.xwd out.png`
Crop/scale with ffmpeg before analysis to keep payloads small.
