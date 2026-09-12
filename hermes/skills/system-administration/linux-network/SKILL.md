---
name: linux-network
description: >-
  Configure Linux networking (static IP, DNS, NetworkManager) and discover LAN
  resources (shared folders, SMB/NFS shares, live hosts). Covers Ubuntu 24.04+
  with netplan + NetworkManager.
---

# Linux Network Configuration & LAN Discovery

## Static IP Setup (Ubuntu 24.04+ with NetworkManager)

### 1. Gather current config
```bash
ip addr show              # interfaces, current IPs, DHCP vs static
ip route show             # default gateway
resolvectl status         # current DNS servers
```

### 2. Identify the network manager
```bash
cat /etc/netplan/*.yaml   # look for renderer: NetworkManager or networkd
```

If `renderer: NetworkManager`, use `nmcli`. If `renderer: networkd`, use netplan YAML directly.

### 3. Set static IP via nmcli
Connection names may contain Chinese/Unicode chars — use exact name from `nmcli con show`.

```bash
# List connections
nmcli con show

# Configure static IP (replace values)
sudo nmcli con mod "<connection-name>" ipv4.addresses 192.168.1.100/24
sudo nmcli con mod "<connection-name>" ipv4.gateway 192.168.1.1
sudo nmcli con mod "<connection-name>" ipv4.dns "8.8.8.8"
sudo nmcli con mod "<connection-name>" ipv4.method manual

# Re-apply
sudo nmcli con down "<connection-name>" && sudo nmcli con up "<connection-name>"
```

### 4. Verify
```bash
ip addr show <interface>        # no 'dynamic' flag means static
ping -c 2 <gateway>             # reachability
```

**Pitfalls:**
- Connection names with spaces or Unicode must be quoted.
- If `down` + `up` drops your SSH session, run from a local terminal or use `nmcli con reload` instead.
- On headless servers with `networkd`, edit the netplan YAML directly then `sudo netplan apply`.

---

## LAN Shared Folder Discovery

### 1. Install tools
```bash
sudo apt-get install -y smbclient nmap avahi-utils
```

### 2. Find live hosts
```bash
sudo nmap -sn 192.168.1.0/24 -T4
```
Note the subnet from `ip route` (typically `192.168.X.0/24`).

### 3. Scan for SMB/CIFS shares (ports 139, 445)
```bash
sudo nmap -p 139,445 --open -T4 192.168.1.0/24
```

For each host with open ports, list shares:
```bash
smbclient -L //<ip> -N    # -N = anonymous/guest
```

### 4. Scan for NFS shares (port 2049)
```bash
sudo nmap -p 2049 --open -T4 192.168.1.0/24
showmount -e <ip>
```

### 5. Scan for mDNS/Bonjour services
```bash
avahi-browse -a -t -r
```

### 6. Browse via GVFS (GNOME virtual filesystem)
```bash
gio mount -l
```

### 8. Scan for common file-sharing alternate ports
Some services use non-standard ports. Check these if standard scans return empty:
```bash
# Full port scan on a likely host (time-consuming)
sudo nmap -p- --open -T4 <target-ip>
```

### 9. Windows Firewall Detection

When SMB ports 139/445 show as `filtered` (not `open` or `closed`), Windows Firewall is actively blocking the connection — the file sharing service itself may still be running on the Windows machine behind the firewall.

**Step 1 — Interpret nmap state correctly:**
```
PORT    STATE     SERVICE
139/tcp filtered  netbios-ssn    # firewall blocking, service may exist
445/tcp filtered  microsoft-ds   # firewall blocking, service may exist
```
"filtered" ≠ "closed". Closed means no service; filtered means the probe was silently dropped.

**Step 2 — Identify the Windows host via HTTP headers:**
```bash
curl -s -I http://<ip>/ 2>&1 | grep -i server
# "Server: Microsoft-IIS/10.0" confirms Windows (IIS is built-in)
```

**Step 3 — Get NetBIOS info (hostname, workgroup, services):**
```bash
nmblookup -A <ip>
```
Output example:
```
DESKTOP-BRITT6R <00> -         B <ACTIVE>    # computer name
WORKGROUP       <00> - <GROUP> B <ACTIVE>     # workgroup
DESKTOP-BRITT6R <20> -         B <ACTIVE>    # <20> = File Server service active
```
The `<20>` flag means the File Server service is registered — strong evidence shares exist.

**Step 4 — Check WS-Discovery port (Windows network discovery):**
```bash
sudo nmap -sU -p 3702 --open <ip>
```

**Step 5 — Solution on the Windows machine:**
On the Windows host, the user needs to:
1. Settings → Network & Internet → Ethernet → change network profile to **"Private"**
2. Control Panel → Windows Defender Firewall → Allow an app through firewall → ensure **"File and Printer Sharing"** has the **Private** box checked
3. After that, SMB ports 139/445 should show as `open` (though Windows login credentials are still required to list/access shares)

**Pitfalls:**
- Router USB storage shares (Xiaomi, TP-Link) use SMB but may refuse guest connections — try with credentials.
- Windows hosts may have firewall blocking SMB (445/139) from Linux even when shares are enabled.
- nmap `-sn` scan requires `sudo` for accurate host detection.
- `showmount` can hang on firewalled hosts — set a timeout wrapper.
- On Windows, guest account is disabled by default → `NT_STATUS_ACCOUNT_DISABLED` is normal; use actual Windows login credentials.
- `NT_STATUS_ACCESS_DENIED` with anonymous login means credentials are required; try `-U <username>%` or `-U <username>%<password>`.
- ThinClient/FreeRDP mounts (under `~/thinclient_drives/`) provide file access without SMB at all — check `gio mount -l` for these before attempting SMB on the remote host.

---

## DNS Troubleshooting (systemd-resolved)

### Symptom: all domain lookups fail, but IP connectivity is fine

```
nslookup google.com        # REFUSED
ping 8.8.8.8               # OK (network itself is up)
```

This means systemd-resolved is running but the upstream DNS server (often a router at 192.168.x.1) is refusing queries.

### Quick diagnosis

```bash
resolvectl status                     # check which DNS servers are configured
nslookup github.com 8.8.8.8           # test against Google DNS directly
```

If `nslookup` against 8.8.8.8 works but default resolver returns `REFUSED`, the upstream DNS is broken.

### Fix: override DNS per interface

```bash
# Find the active interface name
ip addr show | grep "state UP"

# Set Google DNS on the active interface (e.g., enP7s7)
resolvectl dns enP7s7 8.8.8.8 8.8.4.4

# Verify
resolvectl status
nslookup github.com
```

### Make it persistent

The `resolvectl dns` command is per-session. To persist across reboots:

```bash
# Option A: via NetworkManager (if using nmcli)
sudo nmcli con mod "<connection-name>" ipv4.dns "8.8.8.8,8.8.4.4"

# Option B: via resolved.conf (global fallback)
sudo bash -c 'cat >> /etc/systemd/resolved.conf' << 'EOF'
[Resolve]
DNS=8.8.8.8 8.8.4.4
FallbackDNS=1.1.1.1
EOF
sudo systemctl restart systemd-resolved
```

### Common root causes

- **Router DNS service crashed or overloaded** — common on consumer routers under heavy load
- **ISP DNS outage** — upstream provider DNS temporarily unavailable
- **NetworkManager DHCP renewal** reset DNS to a broken gateway
- **systemd-resolved stub listener** at 127.0.0.53 is fine — the problem is always the upstream server it forwards to

---

## Router Port Forwarding Troubleshooting

When a user reports that **external access to a port-forwarded service stopped working** (e.g., "端口转发不行了"), follow this diagnostic flow. Common scenario: a Linux machine behind a consumer router (Xiaomi, TP-Link, etc.) with a port forwarding rule that used to work.

### Diagnostic flow (run in order)

**Step 1 — Verify the service is running and listening**

```bash
ss -tlnp | grep <port>
# Expected: LISTEN on 0.0.0.0:<port> (not just 127.0.0.1)
```

⚠️ If the service binds to `127.0.0.1` only, the router can't reach it. The service must bind to `0.0.0.0` or the LAN IP.

**Step 2 — Verify LAN access works**

Ask the user to access `http://<LAN_IP>:<port>` from a device on the same LAN. If this works, the service and LAN routing are fine — the problem is at the router/ISP layer.

**Step 3 — Check the target machine's firewall**

```bash
sudo ufw status verbose          # UFW
sudo iptables -L INPUT -n        # iptables (look for DROP/REJECT rules)
```

⚠️ UFW "不活动" and empty iptables INPUT chain means no local firewall is blocking — proceed to router checks.

**Step 4 — Test from the server itself to its own public IP (关键诊断步骤)**

This isolates whether the problem is the router or something beyond.

```bash
# Get current public IP
curl -s --max-time 5 ifconfig.me

# Test if external port is reachable FROM the server
curl -s --max-time 10 -o /dev/null -w "HTTP: %{http_code}\n" http://<public_ip>:<external_port>/
# Or TCP-level test:
timeout 5 bash -c 'echo >/dev/tcp/<public_ip>/<external_port>' && echo "OPEN" || echo "CLOSED"
```

**Result interpretation:**

| Result | Meaning | Next step |
|--------|---------|-----------|
| `OPEN` / HTTP 200 | Router forwarding works, ISP is routing | Problem is on the client side (their firewall, their ISP) |
| `CLOSED` / timeout | Router is NOT forwarding the port | Continue to Step 5 |

**Step 5 — Diagnose router-level causes**

When Step 4 returns `CLOSED`, the issue is one of these:

| Cause | How to check | Fix |
|-------|-------------|-----|
| **Router rule needs re-save** | Xiaomi/TP-Link routers sometimes lose NAT state after reboot even if the rule UI still shows it | Edit and re-save the rule, or delete and recreate it |
| **CGNAT (运营商级 NAT)** | WAN口 IP 是 `10.x.x.x`、`100.x.x.x`、`172.16.x.x` 或 `192.168.x.x` | 联系运营商申请公网 IP，或使用内网穿透（frp/ngrok） |
| **Dynamic IP changed** | 当前公网 IP ≠ 之前记录的 IP | 更新 DNS 记录或使用 DDNS |
| **ISP blocking port** | Port 80/443 work but others don't | Try a different port (e.g., 8888, 443), or contact ISP |
| **Router firmware reset** | Rule disappeared after firmware update | Re-create the rule |

### CGNAT detection (common in China)

Many Chinese ISPs (especially China Mobile) assign CGNAT addresses by default. The WAN IP shown in the router is a private address, making port forwarding impossible.

```bash
# Check if public IP is in a private range
python3 -c "
ip = 'CURRENT_PUBLIC_IP'
private_prefixes = ('10.', '100.', '172.16.', '192.168.')
if any(ip.startswith(p) for p in private_prefixes):
    print('⚠️ CGNAT detected — 端口转发无效，需要申请公网IP或使用内网穿透')
else:
    print('✅ 公网IP，端口转发应该有效')
"
```

**Workaround for CGNAT:**
- **Outbound-only tunnel** (Cloudflare Tunnel / Tailscale Funnel): the machine dials out, so there is no inbound port and no forwarding rule to configure — it works through any number of NAT layers. Default choice on a home/office line behind CGNAT; full procedure and mechanism comparison in `references/public-https-tunnels.md`.
- **frp** (内网穿透): Deploy a frp client on the LAN machine, connect to an external VPS with a public IP
- **Contact ISP**: Some ISPs (China Telecom, China Unicom) provide public IP on request

⚠️ **A tunnel hostname is only useful long-term if it is STABLE.** A Cloudflare *Quick* Tunnel (`random-words.trycloudflare.com`) changes on every restart: fine for a smoke test, but it silently breaks any callback/webhook URL registered against it. Anything pasted into a third-party console needs a named tunnel on a domain you control, or Tailscale Funnel's fixed `*.ts.net` hostname. First check whether a public URL is needed at all — pure outbound integrations (pushing messages with an app's own API credentials) need none. See `references/public-https-tunnels.md`.

### Xiaomi router (小强) specific notes

- Router admin: `192.168.31.1` (default subnet `192.168.31.0/24`)
- Port forwarding rules are under **高级设置 → 端口转发**
- After reboot, rules may appear in the UI but need to be **edited and re-saved** to re-apply the NAT rules internally
- Xiaomi routers do NOT support UPnP by default — port forwarding must be manual