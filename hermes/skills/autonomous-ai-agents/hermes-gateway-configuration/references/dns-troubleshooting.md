# DNS Troubleshooting for Gateway Platforms

A platform adapter that connects via WebSocket (receiving messages) but **fails to send replies** is the hallmark of a DNS resolution problem for the platform's HTTP API endpoint.

## Symptom

- `hermes gateway status` shows the platform as **connected**
- The platform **receives** inbound messages (logged in `gateway.log`)
- Sending replies **fails silently** — user sees nothing
- `gateway.log` contains:
  ```
  NameResolutionError: Failed to resolve 'open.feishu.cn' ([Errno -3] Temporary failure in name resolution)
  ```
  or similar for other domains (`ilinkai.weixin.qq.com`, `api.telegram.org`, etc.)

## Two Distinct Failure Modes

### Mode A: `Temporary failure in name resolution` (intermittent)

The DNS server is reachable but occasionally fails to answer for the target domain. Retries may succeed. The gateway log shows intermittent WARNING/ERROR entries.

### Mode B: DNS `REFUSED` (persistent block)

The DNS server actively refuses to answer for the target domain. `host <domain>` returns `REFUSED`, `resolvectl query <domain>` returns `server or network returned error REFUSED`, and `nslookup <domain>` shows `** server can't find <domain>: REFUSED`.

**This is a harder failure:** retries never work. The router's DNS (often `192.168.31.1` on Xiaomi/TP-Link routers in China) actively filters certain domains considered "communication platforms" — including `ilinkai.weixin.qq.com`. The fix requires bypassing the router DNS entirely (see section 4).

### Checking which mode you have

```bash
host ilinkai.weixin.qq.com
# "REFUSED" = Mode B (hard block)
# "Temporary failure" = Mode A (intermittent)

resolvectl query ilinkai.weixin.qq.com
# "REFUSED" = Mode B
# timeout or success = Mode A or no problem

# Python direct DNS check (bypasses system resolver)
python3 -c "
import socket
socket.setdefaulttimeout(3)
try:
    ips = socket.getaddrinfo('ilinkai.weixin.qq.com', 443)
    print(f'OK: {ips[0][4][0]}')
except Exception as e:
    print(f'FAIL: {e}')
"
```

### Cascade Effect

When the router DNS is in Mode B for one domain, it often affects **multiple** domains. A single gateway log showing `REFUSED` for `ilinkai.weixin.qq.com` may coincide with:

- **Provider API failures**: `api.deepseek.com`, `api.openai.com`, or other LLM API endpoints also failing DNS → cron jobs report `Connection error` / `APIConnectionError` in `~/.hermes/logs/agent.log`, even though no gateway configuration changed
- **Model catalog fetch failures**: `hermes-agent.nousresearch.com` returning `Temporary failure in name resolution` on GUI startup
- **Other platform API domains**: `open.feishu.cn`, `api.telegram.org`, etc.

**Diagnostic clue:** If multiple independent services fail at the same time with DNS errors, suspect the router DNS, not individual platform tokens.

## Root Cause

The WebSocket control channel (used for receiving) connects to a different server or IP range than the HTTP API endpoints. When the system DNS server (often the home router's DNS, e.g. `192.168.31.1` on Xiaomi routers) has intermittent failures resolving the API domain, WebSocket stays up while HTTP calls fail.

Common in China behind ISP routers / GFW where DNS can be unstable for non-domestic CDN domains, or where the router actively filters certain communications platform domains (Mode B).

## Debugging Workflow

### 1. Confirm DNS is the issue

Check the gateway log for DNS errors:

```bash
grep -i "name resolution\|Temporary failure\|NameResolutionError\|Failed to resolve" ~/.hermes/logs/gateway.log | tail -10
```

### 2. Check DNS resolution now

```bash
nslookup open.feishu.cn       # or the failing domain
dig open.feishu.cn +short
host open.feishu.cn
python3 -c "import socket; socket.getaddrinfo('open.feishu.cn', 443)"
```

If current resolution works but the log shows intermittent failures, the DNS server is unreliable.

### 3. Identify the DNS server in use

```bash
resolvectl status | grep "DNS Servers"
cat /etc/resolv.conf
```

### 4. Apply fixes (both recommended)

#### A. Add fallback public DNS servers

**Immediate (until reboot):**
```bash
sudo resolvectl dns <interface> <router_ip> <public_dns1> <public_dns2>
# Example:
sudo resolvectl dns enP7s7 192.168.31.1 223.5.5.5 114.114.114.114
```

**Persistent (survives reboot):**
```bash
sudo mkdir -p /etc/systemd/resolved.conf.d/
sudo tee /etc/systemd/resolved.conf.d/dns-servers.conf << 'EOF'
[Resolve]
DNS=192.168.31.1 223.5.5.5 114.114.114.114
FallbackDNS=223.6.6.6 8.8.8.8
EOF
```

Good public DNS servers for China:
- **Alibaba DNS:** `223.5.5.5`, `223.6.6.6`
- **114DNS:** `114.114.114.114`, `114.114.115.115`
- **Baidu DNS:** `180.76.76.76`

Find the interface name with: `resolvectl status | grep -E "^Link"` or `ip link show`.

#### B. Add static /etc/hosts entries

For CDN-hosted API domains (like `open.feishu.cn`), add static entries in case DNS still fails:

```bash
sudo bash -c 'cat >> /etc/hosts << EOF

# Platform API - static DNS bypass
117.68.90.117 open.feishu.cn
60.169.2.33  open.feishu.cn
223.242.32.17 open.feishu.cn
EOF'
```

Find current IPs:\n```bash\ndig <domain> +short | grep -E '^[0-9]'\n\n# If dig is unavailable or router REFUSED blocks it, use nslookup with explicit public DNS:\nnslookup ilinkai.weixin.qq.com 223.5.5.5     # Alibaba DNS (best for China)\nnslookup ilinkai.weixin.qq.com 114.114.114.114 # 114DNS\nnslookup ilinkai.weixin.qq.com 8.8.8.8        # Google DNS (blocked in some CN networks)\n\nThe most reliable method when all public DNS servers are reachable (no GFW blocks) is **nslookup + 223.5.5.5** because Alibaba DNS resolves `.qq.com` domains faster and more reliably than CN-bypassing alternatives. Run multiple DNS servers and compare returned IPs — pick the ones that appear in ≥2 results for the `/etc/hosts` entry.\n\n**DNS-over-HTTPS (DoH) fallback for when even direct nslookup fails:**\n```bash\n# Alibaba DoH (usually works inside China)\npython3 -c \"\nimport urllib.request, json\nurl = 'https://223.5.5.5/resolve?name=ilinkai.weixin.qq.com&type=A'\nreq = urllib.request.Request(url, headers={'Accept': 'application/dns-json'})\nresp = urllib.request.urlopen(req, timeout=10)\ndata = json.loads(resp.read())\nfor a in data.get('Answer', []):\n    if a.get('type') == 1:\n        print(a['data'])\n\"\n```\n> ⚠️ Cloudflare (1.1.1.1) and Google (8.8.8.8) DoH often **time out** from China ISP networks. Try Alibaba (223.5.5.5) DoH first; it's the most reliable from mainland China.\n\n**For REFUSED Mode B domains, write ALL unique IPs to /etc/hosts (not just one):**\n```\n180.101.242.203 ilinkai.weixin.qq.com\n101.227.131.211 ilinkai.weixin.qq.com\n117.89.176.78   ilinkai.weixin.qq.com\n```\nCDN domains like `ilinkai.weixin.qq.com` serve from multiple IPs — writing just one may cause connections to a dead node. Use the intersection of results from 2+ public DNS servers to filter out stale IPs.

**For `ilinkai.weixin.qq.com` (Mode B — hard block):** `/etc/hosts` is the only reliable fix since the router REFUSES all DNS queries for this domain. However, `ilinkai.weixin.qq.com` may be behind a CDN with dynamic IPs, so this is a temporary patch. The durable solution is bypassing the router DNS entirely (method A above) so public DNS servers handle the resolution.

### 5. Verify the fix

```bash
# Test HTTPS connectivity to the API
python3 -c "
import urllib.request, ssl
ctx = ssl.create_default_context()
req = urllib.request.Request('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal', method='POST')
resp = urllib.request.urlopen(req, data=b'{}', context=ctx, timeout=10)
print(f'HTTP {resp.status} - connection OK')
"
```

The fix takes effect immediately for the already-running gateway — `/etc/hosts` and `resolvectl` changes affect new socket connections without a restart. However, if the old token/credential has expired, the next message trigger will refresh it via the now-working DNS path.

## Common Domains by Platform

| Platform | API Domain (HTTP) | Control Channel |
|----------|------------------|-----------------|
| Feishu / Lark | `open.feishu.cn` | WebSocket |
| WeChat / Weixin | `ilinkai.weixin.qq.com` | HTTP long-poll |
| Telegram | `api.telegram.org` | HTTP long-poll |
| DeepSeek API | `api.deepseek.com` | (provider, not gateway) |

## When Platform + Provider Both Fail

A router DNS in Mode B can cause **simultaneous failures** across:
1. Gateway outbound sends (e.g., WeChat replies)
2. LLM provider API calls (e.g., DeepSeek completions in cron jobs)
3. Model catalog fetches (GUI startup)

**What to check first:** resolve any single domain from the affected set. If `host ilinkai.weixin.qq.com` returns `REFUSED`, check `host api.deepseek.com` and `host hermes-agent.nousresearch.com` too. If all return `REFUSED` or `Temporary failure`, the router DNS is the single point of failure — fix it with public DNS fallback (section 4A) and the whole system recovers at once.
