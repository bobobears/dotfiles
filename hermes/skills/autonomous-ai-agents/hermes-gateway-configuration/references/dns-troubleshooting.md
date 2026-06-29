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

## Root Cause

The WebSocket control channel (used for receiving) connects to a different server or IP range than the HTTP API endpoints. When the system DNS server (often the home router's DNS, e.g. `192.168.31.1` on Xiaomi routers) has intermittent failures resolving the API domain, WebSocket stays up while HTTP calls fail.

Common in China behind ISP routers / GFW where DNS can be unstable for non-domestic CDN domains.

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

Find current IPs:
```bash
dig <domain> +short | grep -E '^[0-9]'
```

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
