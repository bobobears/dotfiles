# aria2c Preallocation Trap (large GGUF downloads)

Verified 2026-08-17 while downloading Qwen3.8-27B Q4_K_M (16.8 GB) from ModelScope for LM Studio.

## The trap

aria2c **preallocates the full target file size at download start**. Within seconds `ls -la` / `stat size=` show the final size (e.g. 16810714336), and the aria2c log even prints a `FILE:` line mid-download. The file looks complete while the transfer is actually at 0-40%. In this session the file appeared "done" twice — both verdicts wrong (real progress 41% when re-checked).

**File size is NOT a completion signal.** Neither is the presence of a `FILE:` line in the log, nor a `.part`-less filename, nor `exit_code: 0` from a wrapping shell that backgrounded aria2c with `&` (the shell exits immediately; aria2c keeps running).

## Reliable completion checks (in order)

1. **Wait for the aria2c PROCESS to exit** — `ps -p <PID>` gone. Pattern (background + notify_on_complete):
   ```bash
   while ps -p <PID> > /dev/null 2>&1; do sleep 15; done; echo done
   ```
2. **Then verify sha256** against the expected hash. For LM Studio: `~/.lmstudio/.internal/download-jobs-info.json` → `tasks[].request.sha256`. ModelScope's CDN redirect URL embeds the LFS object ID which equals the content sha256 (`e0/00/82f779...` → `e00082f779...`) — a free cross-check.
3. If sha256 mismatches, **check whether the process is still running before assuming corruption** — a mid-write file yields a bogus hash.

## Chunk-probing a suspected incomplete file

Use Python `seek/read`, NOT `dd bs=1 skip=N` (misbehaves on big offsets — returned identical garbage hashes for every offset in this session):

```python
f = open(path, 'rb')
for pos in [0, 5_000_000_000, 10_000_000_000, 16_790_000_000]:
    f.seek(pos); chunk = f.read(1_048_576)
    zeros = chunk.count(b'\x00')
    print(pos, f'zeros={zeros}/{len(chunk)}')
# zeros == len(chunk) at large offsets → still preallocated, data not yet written
```

Note: a file can be fully preallocated AND fully written (real 16 GB of blocks) while some regions are still zeros — `du`/`stat blocks` matching size does NOT prove completion either.

## Why it matters for the LM Studio workflow

The ModelScope-acceleration workflow in `api-download-and-modelscope-fallback.md` step 3 depends on knowing when the download is truly finished before copying files into LM Studio's `savePath`. Copying a preallocated-but-partial file there produces a corrupt GGUF that LM Studio will mis-handle or re-download.

## Relation to other docs

- `api-download-and-modelscope-fallback.md` — the full LM Studio API-download + ModelScope workflow.
- `model-download-china.md` — general China-network GGUF download guidance.
- Memory note: "aria2c 注意：-A 是 --allow-overwrite 简写，设置 UA 必须用 --user-agent=..." also applies to the download commands here.
