# Proxy Setup Debug Reference

## Error Patterns & Meanings

| Error | Exit Code | Meaning |
|-------|-----------|---------|
| `curl: (28) connection timed out` | 28 | Host unreachable or connection dropped (GitHub CDN) |
| `curl: (6) Could not resolve host` | 6 | DNS failure (ghproxy.net etc.) |
| `curl: (7) Failed to connect` | 7 | Host resolved but connection refused or timed out |
| `hermes skills install timed out` | 124 | `raw.githubusercontent.com` DNS-polluted (→ 0.0.0.0); use ghproxy fallback |
| `Sec scan: DANGEROUS/CRITICAL` | N/A | Internal security scanner blocks install — `--force` does not override dangerous verdict |
| `aria2 ETA: 45m` | N/A | Download progressing but very slow (20-100 KiB/s) |
| `HTML document, ASCII text` (5-10 KB) | 0 | GitHub mirror returned Cloudflare/WAF challenge, not real file |
| `E: Unable to locate package` | 0 | Repo not configured correctly or unreachable |
| `snap: server misbehaving` | 1 | snapcraft.io DNS failing from China |

## Tested Mirror Status (June 2026)

### GitHub Release Proxies
| Mirror | Status | Notes |
|--------|--------|-------|
| `ghproxy.net` | ⚠️ Partial | Works for raw.githubusercontent.com content; git clone/hermes skills install may timeout |
| `mirror.ghproxy.com` | ❌ Unreachable | DNS/connectivity failure |
| `gh.api.99988866.xyz` | ❌ Unreachable | DNS/connectivity failure |
| `download.fgit.cf` | ❌ Cloudflare | Returns CF challenge page |
| `gh.h233.eu.org` | ❌ Cloudflare | Returns CF challenge page |
| `mirrors.tuna.tsinghua.edu.cn/github-release/` | ✅ Reachable | Works, but only serves cached packages |

### Direct Sources
| Source | Status | Notes |
|--------|--------|-------|
| `github.com` (web) | ✅ Works | Ping 104ms, DNS works |
| `github.com/.../releases/download/` | ⚠️ Slow | 20-100 KiB/s via aria2 |
| `pypi.org` | ✅ Works | Fast, no throttling |
| `apt.v2raya.org` | ❌ Unreachable | Connection timeout |
| `snapcraft.io` | ❌ DNS fail | `server misbehaving` |
| `launchpad.net` (PPA) | ❌ DNS fail | Specific to canonical PPAs |
| `mirrors.tuna.tsinghua.edu.cn` | ✅ Works | Fast |

## DNS Pollution: raw.githubusercontent.com

In mainland China, `raw.githubusercontent.com` is DNS-polluted — it resolves to
`0.0.0.0` (not a slow connection, a block). This affects every tool that fetches
from it: `hermes skills install`, `curl`, `wget`, `pip install` from GitHub raw URLs.

**Fix:** Prepend `https://ghproxy.net/` to the URL, e.g.:

```bash
curl -sL "https://ghproxy.net/https://raw.githubusercontent.com/owner/repo/branch/file" -o output
```

See `references/ghproxy-usage-patterns.md` for the full catalog of ghproxy patterns.

## User Disclosure Pattern

When a user in a restricted network asks to install a proxy/GitHub acceleration tool:

1. **First verify they actually have a proxy subscription** — many users assume Clash Verge IS the proxy rather than a client that needs a subscription.
2. If they only have GitHub credentials, recommend SSH key auth + Git mirror URLs as the practical alternative.
3. Only proceed with GUI client installation after confirming they have (or are willing to obtain) a subscription.
