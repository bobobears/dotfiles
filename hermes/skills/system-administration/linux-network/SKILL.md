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