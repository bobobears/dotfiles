# Publishing a LAN Service to the Public Internet (HTTPS, behind NAT/CGNAT)

Use when a service on this machine must be reachable from outside — a platform callback
or webhook URL, an OAuth redirect, a mobile-facing page — and the box sits behind
carrier NAT with no inbound 80/443.

## Step 0 — Decide whether you need this at all

Most "expose my local system" requests do NOT need a public address. Sort the request by
**direction** before building anything:

| Requirement | Public URL? | Stable hostname? |
|---|---|---|
| LAN users reach the service (same Wi-Fi/VPN) | No | No |
| The service calls a cloud API outbound (push notification, sending messages) | No | No |
| A third party must POST *into* your service (callback, webhook, event subscription) | Yes, HTTPS | Yes |
| A page is loaded by a third-party client (in-app browser, mobile app, 工作台 H5) | Yes, HTTPS | Yes |

Only the last two rows justify a tunnel. Say this up front — it saves the user buying a
domain to solve a problem a LAN address already solves.

**Outbound-only needs no URL at all.** Before reaching for a tunnel, check whether the
integration has a pure-outbound mode: e.g. a WeCom 自建应用 pushing app messages needs
only `corpid` + `secret`, and the public callback URL is required only for *inbound*
events or a hosted web app. "We need to push office notifications" is not a tunnel task.

## Step 1 — Pick the exposure mechanism

| Mechanism | Hostname | Cost | Notes |
|---|---|---|---|
| Cloudflare **Quick** Tunnel | random `*.trycloudflare.com` | free, no account | **Ephemeral — changes every restart.** Smoke tests only. |
| Cloudflare **Named** Tunnel | your own domain on Cloudflare | domain price | Permanent, stable. Requires the domain's DNS hosted at Cloudflare — Cloudflare does not issue free domains, so there is no way around owning one for this path. |
| Tailscale Funnel | fixed `<machine>.<tailnet>.ts.net` | free (documented as available on all plans) | No domain needed, cert auto-issued. Ports 443/8443/10000 only, bandwidth-limited, relay outside mainland China → higher latency. |
| frp to your own VPS | your VPS/domain | VPS cost | Full control; needs a VPS with a public IP. |

Rule of thumb: **a URL you register in someone else's console must be permanent.** If the
value is only ever read by you in a browser, a Quick Tunnel is enough.

## Step 2 — Install cloudflared without root

```bash
mkdir -p ~/.local/bin
# GitHub direct frequently times out from mainland China — fetch via a mirror, then
# verify against the vendor's own apt index before trusting the bytes
# (pattern: linux-package-install-arm64 skill).
curl -fL --retry 3 -o /tmp/cloudflared \
  "https://<mirror>/https://github.com/cloudflare/cloudflared/releases/download/<ver>/cloudflared-linux-arm64"
chmod +x /tmp/cloudflared && /tmp/cloudflared --version && mv /tmp/cloudflared ~/.local/bin/cloudflared
```

## Step 3 — Quick Tunnel (smoke test)

```bash
# keep the origin on loopback — the tunnel is the ONLY public path (see Pitfalls)
python3 -m http.server 8645 --bind 127.0.0.1 --directory /tmp/demo &

~/.local/bin/cloudflared tunnel --url http://127.0.0.1:8645 --no-autoupdate \
  2>&1 | tee /tmp/demo/cloudflared.log &

# the hostname is printed once, inside a box of ASCII art — grep it out
grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' /tmp/demo/cloudflared.log | head -1
```

## Step 4 — Verify from outside, not from localhost

A 200 fetched on the origin machine proves nothing about the tunnel. Assert all four:

```bash
curl -sS -o /tmp/body -w '%{http_code} ssl_verify=%{ssl_verify_result}\n' https://<hostname>/
grep -c '<a marker string you put in the served page>' /tmp/body
ss -tlnp | grep 8645          # must still be 127.0.0.1, never 0.0.0.0
curl -s --max-time 5 ifconfig.me   # record the egress IP you are testing through
```

- `ssl_verify_result=0` = the edge certificate validated.
- The marker grep proves the edge is fronting *your* process, not a stale tunnel or the
  edge's catch-all.
- The `ss` check proves you did not also open the service to the whole LAN.
- For a human-visible check, have the user open the URL on a phone on **mobile data**
  (not Wi-Fi, which can hairpin back through the same NAT and mask a failure).

## Step 5 — Named Tunnel (permanent, requires a domain)

Create a named tunnel in the Cloudflare Zero Trust dashboard, map a public hostname to
`http://127.0.0.1:<port>`, then run it with the issued token:

```bash
cloudflared tunnel run --token <TUNNEL_TOKEN>     # foreground; `service install` needs root
```

The permanent hostname is what you paste into the third-party console.

## Pitfalls

- **Registering an ephemeral tunnel URL is the classic trap.** A `trycloudflare.com` Quick
  Tunnel URL works perfectly in testing, then dies on the next restart and silently breaks
  every callback registered against it. Choose Named Tunnel or Tailscale Funnel *before*
  pasting any URL into a third-party console.
- **HTTPS is not optional for platform callbacks.** WeCom — and most Chinese platforms —
  reject plain-HTTP callback URLs outright; the endpoint must terminate TLS with a valid
  certificate. Quick Tunnels and Funnel both provide one, so do not waste time adding TLS
  to the origin: the edge terminates it and the origin can stay plain HTTP on loopback.
- **A tunnel makes the service world-readable.** Keep the origin bound to `127.0.0.1` and
  put authentication in front (Cloudflare Access, a shared token in path/header) if the
  content is not meant to be public. A tunnel is not a private network.
- **Do not offer port-forwarding as the "simpler" alternative before checking CGNAT.**
  When the router's WAN address is in `10./100./172.16./192.168.`, no forwarding rule will
  ever work — run the CGNAT check in the parent skill first instead of promising it.
- **Expose one specific service port per tunnel.** Do not point a tunnel at a reverse proxy
  that fans out to everything on the box.
- **Clean up after the demo.** Stop the tunnel and the origin when the verification is done
  — a forgotten tunnel is a permanently open door. Kill by PID (see the `pkill -f`
  self-kill pitfall in the `hermes-gateway-configuration` skill).
