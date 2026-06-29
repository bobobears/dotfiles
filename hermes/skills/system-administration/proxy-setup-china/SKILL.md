---
name: proxy-setup-china
description: >-
  Install proxy clients (Clash Verge, v2rayA, Hiddify, etc.) on Linux from
  network-restricted environments (e.g. mainland China). Covers multi-mirror
  fallback, PyPI/pip workaround, and Git-only acceleration as a fallback when
  no subscription is available.
---

# Proxy Setup in Network-Restricted Environments (China)

This skill covers deploying proxy/acceleration software on Linux when GitHub,
snapcraft, flatpak, and common apt sources are throttled or unreachable.

## 1. Initial Diagnosis

Check what's actually reachable before choosing a strategy:

```bash
# GitHub basic connectivity
ping -c 2 github.com
nslookup github.com

# Check GitHub Release CDN specifically
curl -sI --connect-timeout 10 \
  "https://github.com/clash-verge-rev/clash-verge-rev/releases/latest"

# Check apt repos
curl -sI --connect-timeout 10 "https://mirrors.tuna.tsinghua.edu.cn"
curl -sI --connect-timeout 10 "https://pypi.org"

# Check existing local proxies
ss -tlnp | grep -E '7890|7891|1080|1081|8080'
env | grep -i proxy
```

**Typical pattern in China:** GitHub ping works, GitHub website loads, but **GitHub Release assets** (CDN) are extremely slow (20-100 KiB/s) or time out. PyPI usually works. Some apt repos are blocked.

## 2. Download Strategies (ordered by preference)

### Strategy A: aria2 multi-threaded download (slow but reliable)
Use when single-connection curl/wget time out:

```bash
sudo apt install -y aria2
aria2c -x 4 -s 4 --connect-timeout=15 --timeout=600 \
  --dir=/tmp --out=<package.deb> \
  "https://github.com/<owner>/<repo>/releases/download/<tag>/<file>"
```

Run as a background process. At ~50-150 KiB/s, expect 10-40 minutes for a 76MB .deb.

### Strategy B': Partial ZIP extraction (last resort when all downloads time out)

When full archive download fails repeatedly (common for repos >50MB at
20-50 KiB/s), extract whatever the truncated zip contains:

1. Download with aria2c — stop at any point (or let it time out)
2. Use manual `PK\x03\x04` scanning to extract intact files
3. Fill gaps via GitHub API (small files) or ghproxy for raw content

Full code and procedure: see `references/truncated-zip-extraction.md`.

### Strategy C: GitHub mirror proxies
Try each in order — some go down periodically:

```bash
# Common proxy services
for proxy in \
  "ghproxy.net" \
  "mirror.ghproxy.com" \
  "gh.api.99988866.xyz" \
  "download.fgit.cf" \
  "gh.h233.eu.org"; do
  url="https://${proxy}/https://github.com/..."
  curl -sL --connect-timeout 15 --max-time 120 -o /tmp/pkg.deb "$url"
  file /tmp/pkg.deb | grep -q "HTML" && continue  # skip CF challenge pages
  ls -lh /tmp/pkg.deb && break
done
```

**Caveat:** Some proxies return Cloudflare challenge HTML (5-10 KiB) instead of the real file. Check with `file` or `head -c 100`.

### Strategy C: PyPI/pip (best for Python-based tools)
PyPI is usually fully accessible in China:

```bash
pip3 install pproxy          # Pure Python SOCKS5/HTTP proxy
pip3 install shadowsocks     # Shadowsocks client
```

**pproxy** is particularly useful — it can run as both server and client, supports SOCKS5/HTTP/HTTPS/SOCKS4, and requires no external binaries.

### Strategy D: Official apt/snap/flatpak mirrors
```bash
# TUNA mirror for flatpak
sudo flatpak remote-add --if-not-exists flathub \
  https://mirrors.tuna.tsinghua.edu.cn/flathub

# Snap proxy
sudo snap set system proxy.http="http://127.0.0.1:7890"
sudo snap set system proxy.https="http://127.0.0.1:7890"
```

**Often broken** in practice due to CDN issues — fall back to A/B/C.

## 3. Git-Only Acceleration (no proxy subscription needed)

If the user only needs to speed up `git clone/push/pull` and doesn't have a proxy subscription:

### SSH key auth (bypasses HTTPS rate limits)
```bash
# Generate key
ssh-keygen -t ed25519 -C "your-email@example.com"
cat ~/.ssh/id_ed25519.pub

# Add to GitHub: https://github.com/settings/keys
# Test
ssh -T git@github.com
```

### ghproxy.net mirror (general purpose)

`ghproxy.net` wraps GitHub raw content URLs so they resolve when
`raw.githubusercontent.com` is DNS-polluted (common in China — resolves to
`0.0.0.0`). Use it for Git, curl downloads, and Hermes skill installs.

```bash
# Git clone via mirror
git clone https://ghproxy.net/https://github.com/user/repo.git
# Git remote
git remote add mirror https://ghproxy.net/https://github.com/user/repo.git

# Raw content download (e.g. SKILL.md, scripts)
curl -sL "https://ghproxy.net/https://raw.githubusercontent.com/owner/repo/branch/file"

# Hermes skills install (when skills.sh / raw.github.com unreachable)
# See references/ghproxy-usage-patterns.md for full workflow
```

Full patterns (curl, git, Hermes skill install, release assets, verification):
see `references/ghproxy-usage-patterns.md`.

### Post-Extraction Recovery

After downloading a truncated GitHub archive, see:
`references/truncated-zip-extraction.md` — covers manual extraction, the
iterative dependency chase for missing Python modules, null-byte corruption
fixes, and batch recovery strategies.

## 4. If User Has No Proxy Subscription

**Ask explicitly** — Clash Verge and similar clients are useless without subscription nodes.

Available paths:
1. **Purchase an airport subscription** (search "便宜机场" or sites like Just My Socks)
2. **Self-host on a VPS** (buy an overseas VPS, install Shadowsocks/V2Ray/wireguard)
3. **Git-only via SSH** (no general proxy, but Git works at full speed)
4. **Use Gitee mirror** — mirror GitHub repos to Gitee, then clone from there

## Pitfalls

- **Don't assume apt sources are reachable.** v2rayA's apt repo (`apt.v2raya.org`) and snapcraft.io are often unreachable from China.
- **Cloudflare challenge pages** from GitHub mirrors look like real downloads (5-10 KiB HTML). Always `file <downloaded-file>` to check.
- **aria2 with too few threads** (x2) may be slower than x4-x8. But too many threads (x16+) can trigger rate limiting.
- **Snap has its own proxy config** separate from system env vars — `sudo snap set system proxy.{http,https}=...` is required, not env vars.
- **User has GitHub credentials ≠ proxy subscription.** GitHub password/token only helps with Git API rate limits, not general traffic acceleration.
- **Launchpad PPAs** (e.g. canonical-nvidia) often have DNS resolution failures in China — expect warnings from `apt update`.
- **Python via pip**: use `pip3` (not pip) and activate a venv first to avoid PEP 668 issues.

## Verification

After installing a proxy client, verify it's running and exposed locally:

```bash
# Check listening ports
ss -tlnp | grep -E '7890|7891|1080'

# Test proxy works
curl -x http://127.0.0.1:7890 --connect-timeout 10 https://icanhazip.com
# The IP should be from the proxy exit node, not your direct connection

# For Git proxy
git config --global http.proxy 'http://127.0.0.1:7890'
git config --global https.proxy 'http://127.0.0.1:7890'
git clone --depth=1 https://github.com/...  # test speed
```
