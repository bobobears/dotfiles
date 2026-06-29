# Diagnosing Hung / Stuck / Long-Running Processes

## When to Use

A user says something is "not responding", "taking too long", "stuck", or asks "is the process still alive?" You need to determine:

- Is the process alive? Yes/No
- If alive, is it making progress or truly stuck?
- If stuck, where is it stuck (what's it waiting for)?
- What subprocesses are involved?

## Quick Triage Order

```bash
# 1. Check if process exists
ps aux | grep -i <name> | grep -v grep

# 2. Get detailed state (etime = elapsed time, STAT = process state)
ps -o pid,etime,%cpu,%mem,stat,wchan,cmd -p <PID>

# 3. Trace the process tree
pstree -p <PID>
```

## State Interpretation

| STAT | Meaning | Implication |
|------|---------|-------------|
| R / R+ | Running | Actively using CPU — check %CPU |
| S / S+ | Sleeping (interruptible) | Normal idle — waiting for something |
| D / D+ | Sleeping (uninterruptible) | I/O wait — often disk or NFS |
| Z | Zombie | Dead but not reaped by parent |
| T | Stopped | Stopped by signal |
| Sl+ | Multi-threaded, sleeping | Normal for node/npm |

## When Process is Alive but Appears Stuck

### 1. Check What It's Waiting On (`wchan`)

```bash
cat /proc/<PID>/wchan
```

Common values:
- `do_wait` — waiting for a child process to exit (the parent is alive, the child may be doing real work)
- `epoll_wait` — waiting on network I/O
- `poll_schedule_timeout` — sleeping (timer or wait)
- `inotify_read` — watching filesystem
- `futex_wait_queue_me` — waiting on a lock or mutex
- `pipe_wait` — blocked on pipe I/O

### 2. Check the Kernel Stack

```bash
cat /proc/<PID>/stack
```

Gives the kernel call chain showing exactly what kernel function it's blocked in.

### 3. Trace the Process Tree

```bash
pstree -p <PID>
```

Find the *deepest* child — the actual worker. Check if it's the one doing work or also waiting.

### 4. Check Child Process State

```bash
ps --ppid <PID> -o pid,etime,%cpu,%mem,stat,cmd
```

Key checks:
- Is the child using CPU? If > 0%, it's working.
- How long has it been running? Compare elapsed time to expectations.
- Is the child itself sleeping? Check its wchan too.

### 5. Check Network Activity

```bash
ss -tupn | grep <pid>
```

- `ESTAB` + send/receive buffers growing = downloading/uploading
- `TIME_WAIT` / `CLOSE_WAIT` = finished connections, not current work
- No connections = likely CPU-bound or I/O-bound, not network-bound

### 6. Check Working Directory

```bash
readlink /proc/<PID>/cwd
```

Confirms what directory the process is running in — essential for understanding what it's installing or building.

### 7. Check File Descriptors

```bash
ls -la /proc/<PID>/fd/
```

Reveals:
- Open log files (check `w` mode files for recent writes)
- Network sockets (check socket inode against `ss`)
- Pipe/eventfd — inter-process communication, could mean blocked on IPC
- `anon_inode` — epoll, io_uring, eventfd (normal for async I/O)

### 8. Read Log Files

Follow open file descriptors to log paths and read them:

```bash
# From fd listing, find writable log files and check them
tail -50 /path/to/gui.log
tail -50 /path/to/errors.log
```

Empty log files that the process opened but hasn't written to = process hasn't reached the logging stage yet.

### 9. Check Command Line

```bash
cat /proc/<PID>/cmdline | tr '\0' ' '
```

Confirms the exact command — useful when `ps` truncates long command lines. Null-separated, so `tr` is needed for readability.

### 10. Check Related State

For npm/pip/installer processes, check:

```bash
# npm cache growth (check last modified times)
ls -lt /home/user/.npm/_cacache/content-v2/sha512/ | head -5

# Node_modules progress
ls /path/to/node_modules/ | wc -l

# Package manager cache size
du -sh /home/user/.npm/_cacache/
```

If cache is growing or last-modified times are recent → actively downloading.
If cache hasn't changed in minutes → possibly stuck on a single large package, network, or resolution.

## Common Patterns

### "npm ci is taking forever"

```
hermes desktop (PID) ── npm ci (PID) ── node (PID)
                    do_wait          Sl+ (sleeping)     ESTAB to registry.npmjs.org
```

- **Alive, working.** `npm ci` is downloading packages. First time can be 5-15 minutes.
- Check npm cache last-modified times for progress.
- Check network connection state and send/receive buffer.
- **Options:** Wait, or Ctrl+C and re-run with visible progress: `cd <cwd> && npm ci`

### "pip install is stuck"

```
python -m pip install (PID)
               S+ (sleeping with ESTAB connections)
```

- Check if it's resolving dependencies (CPU) or downloading (network).
- Check if pip cache is growing.
- Common cause: dependency resolver hanging on conflicting requirements.

### "build script hung"

```
make (PID) ── gcc/clang (PID) ── cc1 (PID)
        do_wait          R+               R+
```

- Parent is waiting for child (normal).
- Check if child has high CPU (compiling) or is stuck on I/O.
- Check `wchan` of each leaf process.

### "server won't start / no output"

```
node/python server.js (PID)
               S+ (sleeping)
```

- Check if a port is already in use (`ss -tlnp | grep <port>`).
- Check if there's an open log fd and read it.
- Try connecting to the port to see if it's actually listening.

### npm/node: Downloading a Large Binary (Electron, Puppeteer, Chromium)

When `npm ci` or `npm install` is slow, the cause is often a large platform-specific binary being downloaded. Detect it:

```bash
# Check for in-progress Electron download
ls -lh /tmp/electron-download-*/ 2>/dev/null
# Watch its growth to confirm progress:
watch -n 5 'ls -lh /tmp/electron-download-*/ 2>/dev/null'

# Check the node process's /proc for open download paths
ls -la /proc/<node_PID>/fd/ | grep tmp
# If linked to something like "electron-...zip", it's downloading
```

The file grows steadily. Electron binaries are 100-200 MB. If the temp file isn't growing for 60+ seconds despite an `ESTAB` connection, the download may be stalled (slow registry, rate limit, or DNS issue).

### Orphaned Child Processes After Kill

When you kill a parent process that's stuck in `do_wait`, its child may **survive as an orphan** — still running, holding file handles, ports, or locks. This causes resource conflicts when you re-run the same command.

```bash
# Before killing, note the child PIDs and what they're doing
pstree -p <PID>

# After killing the parent, check for orphans
ps aux | grep <child_cmd> | grep -v grep

# Clean up orphans gently first, then force
kill <orphan_PID>; sleep 1
ps -p <orphan_PID> 2>/dev/null && kill -9 <orphan_PID> || echo "cleaned"
```

**Always clean orphans before re-running.** A second `npm ci` or `pip install` with the first one's node still writing to npm cache can corrupt state.

## Summary: Is It Alive and Working?

| Signal | Alive + Working | Alive + Stuck | Dead |
|--------|----------------|---------------|------|
| CPU usage | > 0% | 0% for 1+ min | N/A |
| Network | ESTAB, data flowing | ESTAB but no activity | N/A |
| Cache/files | Last-modified advancing | No changes in minutes | N/A |
| wchan | Varies (running) | `do_wait` with idle child | N/A |
| Process in ps | Yes | Yes | No |
| Exit code | N/A | N/A | Check with `$?` |
