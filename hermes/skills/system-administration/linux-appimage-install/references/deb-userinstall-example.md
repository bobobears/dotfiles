# Deb User-Level Install Example: QQ Linux (arm64)

Example from an actual session: installing QQ Linux (arm64 deb) on DGX Spark (Ubuntu, aarch64, no sudo).

## Step 1: Find the real download URL

Many official download pages use JS to generate download links. Extract the config:

```bash
# 1. Resolve the CDN
host cdn-go.cn 8.8.8.8

# 2. Fetch the JS config that contains the download URLs
curl -sL --resolve "cdn-go.cn:443:<IP>" \
  -H "User-Agent: Mozilla/5.0" \
  "https://cdn-go.cn/qq-web/im.qq.com_new/latest/rainbow/linuxConfig.js"
```

The JS config is a JSON-like object: `{"version":"3.2.29","armDownloadUrl":{"deb":"https://...arm64_01.deb",...}}`

## Step 2: Download with CDN workaround

The download CDN (e.g. `qqdl.gtimg.cn`) may also need --resolve:

```bash
host qqdl.gtimg.cn 8.8.8.8 | grep "has address"
# Pick one IP
curl -sL \
  --resolve "qqdl.gtimg.cn:443:<IP>" \
  -H "User-Agent: Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) QQ/3.2.29" \
  -H "Referer: https://im.qq.com/linuxqq/" \
  -o /tmp/app.deb \
  "https://qqdl.gtimg.cn/qqfile/QQNT/9.9.31/release/.../QQ_3.2.29_260528_arm64_01.deb"
```

## Step 3: Extract deb without sudo

```bash
# Extract to temp dir
dpkg -x /tmp/app.deb /tmp/app_extracted
ls /tmp/app_extracted/opt/
ls /tmp/app_extracted/usr/
```

## Step 4: Install to user space

```bash
# Copy to ~/.local/opt/
mkdir -p ~/.local/opt
cp -r /tmp/app_extracted/opt/<AppName> ~/.local/opt/

# Make binary accessible
mkdir -p ~/.local/bin
ln -sf ~/.local/opt/<AppName>/<binary> ~/.local/bin/

# Copy desktop file
mkdir -p ~/.local/share/applications
cp /tmp/app_extracted/usr/share/applications/<app>.desktop ~/.local/share/applications/

# Fix paths in desktop file
sed -i "s|Exec=/opt/<AppName>/<binary>|Exec=$HOME/.local/opt/<AppName>/<binary>|g" \
  ~/.local/share/applications/<app>.desktop

# Copy icons
cp -r /tmp/app_extracted/usr/share/icons/hicolor ~/.local/share/icons/

# Fix icon path in desktop file
sed -i "s|Icon=/usr/share/icons|Icon=$HOME/.local/share/icons|g" \
  ~/.local/share/applications/<app>.desktop
```

## Step 5: Handle chrome-sandbox (Electron apps)

Electron apps need `--no-sandbox` when sandbox helper can't be owned by root:

```bash
# Test
~/.local/opt/<AppName>/<binary> --no-sandbox

# Update desktop file
sed -i 's|Exec=\(.*\)<binary>|Exec=\1<binary> --no-sandbox|g' \
  ~/.local/share/applications/<app>.desktop
```

## Step 6: Verify

```bash
# Check binary in PATH
which <binary>
# Check desktop entry
cat ~/.local/share/applications/<app>.desktop
# Try launching
~/.local/bin/<binary> --no-sandbox --version
```

## Key pitfalls

- **DNS flaky**: Always resolve domains with `host <domain> 8.8.8.8` first, use `--resolve` for reliable access
- **CDN 403 on arm64**: Some CDNs block based on User-Agent. Try matching the app's own UA string
- **Vulkan errors**: `VK_ERROR_INCOMPATIBLE_DRIVER` is harmless for Electron apps — they fall back to software rendering
- **sandbox**: If `chrome-sandbox` SUID check fails, `--no-sandbox` is the fix (safe for per-user installs)
