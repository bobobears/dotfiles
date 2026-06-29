# GitHub Mirror Options for China / Restricted Networks

## HTTPS Mirrors (for `git clone` / `curl`)

Tested from mainland China (Ubuntu 24.04 ARM64, no proxy, 2026-06):

| Mirror | URL Format | Status | Notes |
|--------|-----------|--------|-------|
| ghproxy.net | `https://ghproxy.net/https://github.com/...` | ✅ Working | HTTP 200, reliable |
| hub.fgit.cf | `https://hub.fgit.cf/...` | ⚠️ Unreachable | DNS or Cloudflare blocked |
| hub.gitmirror.com | `https://hub.gitmirror.com/...` | ⚠️ Unreachable | DNS resolution failed |
| ghproxy (alt) | `https://gh.h233.eu.org/...` | ⚠️ Cloudflare challenge | Returns "Just a moment..." CAPTCHA page |
| fgit.cf | `https://download.fgit.cf/...` | ⚠️ Cloudflare challenge | Same CAPTCHA issue |
| mirrors.tuna.tsinghua.edu.cn/github-release | `https://mirrors.tuna.tsinghua.edu.cn/github-release/<owner>/<repo>/<tag>/<file>` | ⚠️ 404 for most | Only caches popular repos; Clash Verge not cached |

## Recommended Setup

For most users, **ghproxy.net** is the most reliable tested option:

```bash
# Git clone acceleration
git config --global url."https://ghproxy.net/https://github.com/".insteadOf "https://github.com/"

# Generic curl download acceleration
# Use: curl -LO https://ghproxy.net/https://github.com/...
```

## Download Acceleration Strategy (for .deb / binaries)

When downloading GitHub release assets (binaries, .deb, AppImage):

1. **Try ghproxy.net first** — prepend `https://ghproxy.net/` to the GitHub URL
2. **If that fails, try `aria2c -x 4 -s 4`** — multi-connection can sometimes get through where single-stream curl times out (tested: ~70 KiB/s sustained, 76MB in ~30min)
3. **Add DNS retries** — GitHub release assets redirect to `release-assets.githubusercontent.com` which may have transient DNS failures
4. **Last resort: SSH tunnel** — if you have another machine with better connectivity, SSH tunnel to it

## SSH Connectivity Notes

- SSH to `github.com:22` (git protocol) works reliably from China
- Git-over-SSH is faster than HTTPS for push/pull even with mirrors
- First SSH connection: `ssh -T -o StrictHostKeyChecking=accept-new git@github.com`
- If port 22 is blocked, try port 443: add to `~/.ssh/config`:
  ```
  Host github.com
      HostName ssh.github.com
      Port 443
  ```

## Notes on Package Managers

| Package Manager | China Accessibility | Alternative |
|----------------|:---:|------------|
| apt (archive.ubuntu.com) | ✅ Slow but works | Use `mirrors.tuna.tsinghua.edu.cn` |
| snap (snapcraft.io) | ❌ Blocked | Use snap with Chinese mirror, or skip |
| flatpak (flathub) | ⚠️ Unreliable | Use `mirrors.tuna.tsinghua.edu.cn/flathub` |
| pip (pypi.org) | ✅ Works | Use `mirror.tuna.tsinghua.edu.cn/pypi` |
