---
name: linux-package-install-arm64
description: >-
  Install Linux applications on ARM64 (aarch64) from non-deb packages (RPM,
  AppImage, tar.gz, manual extract) on Ubuntu/Debian. Covers RPM→cpio
  extraction, sandbox fixups, .desktop registration, and dependency checks.
  Useful when upstream only ships x86_64 .deb or when network-restricted
  environments block apt.
tags:
  - arm64
  - aarch64
  - rpm
  - alien
  - alternative-install
  - ubuntu
  - manual-install
---

# Linux Package Install (ARM64 / Non-Deb)

## When to use

- The user downloaded a Linux app package in RPM, AppImage, or `.tar.gz` format
- The system is **ARM64 (aarch64)** — e.g. NVIDIA DGX Spark, Raspberry Pi, Apple M-series via VM
- The app has no official ARM64 `.deb` or the `.deb` is for x86_64 only
- Network is restricted (DNS/proxy issues) — `apt-get` fails on `ports.ubuntu.com`

## Workflow

### 1. Check what you're dealing with

```bash
file <package>          # ELF 64-bit ARM aarch64?
ls -lh <package>        # size
```

### 2. Extract the RPM

Two options — prefer **rpm2cpio** when installable:

```bash
# Option A: install rpm2cpio (small, fast)
sudo apt-get install -y rpm2cpio

# Option B: use rpm2cpio + cpio to extract
mkdir -p extract-dir && cd extract-dir
rpm2cpio ../<package>.rpm | cpio -idmv
```

> **If apt-get fails** (DNS / network-restricted): `rpm2cpio` is a tiny binary (~30KB). Pre-download the `.deb` via a mirror or use a cached copy, or try `dpkg -x` on an already-cached debs.

### 3. Inspect extracted structure

```bash
find . -type f | head -30
```

Common RPM layout:
| Path | Purpose |
|------|---------|
| `./usr/local/bin/` | Binary executables |
| `./usr/local/lib/<app>/` | Library files |
| `./usr/local/share/<app>/` | Assets (icons, res.db, etc.) |
| `./usr/share/applications/<app>.desktop` | Desktop entry |

### 4. Install to system

```bash
sudo cp -r ./usr/local/bin/* /usr/local/bin/
sudo mkdir -p /usr/local/share/<app>
sudo cp ./usr/local/share/<app>/* /usr/local/share/<app>/
sudo mkdir -p /usr/local/lib/<app>
sudo cp /usr/share/applications/<app>.desktop /usr/share/applications/
```

### 5. Verify existing installation first

Before extracting or installing, check if the user already has a newer version:

```bash
which <app>
ls -la ~/.local/bin/<app>       # user-local symlink?
ls ~/.local/opt/<AppName>/      # modern self-contained install?
```

If an existing version is **newer** (check `--version` or app logs), **do not downgrade** — abort or ask the user.

### 6. Verify dependencies

```bash
ldd /usr/local/bin/<binary> | grep "not found"
```

If any **not found**, install the missing libs:
```bash
sudo apt-get install -y <lib-package-name>
```

### 7. Test run

```bash
/usr/local/bin/<binary>
```

> Best run with `timeout 3` to test launch without blocking.

### 8. (If needed) Fix sandbox permissions

Electron-based apps (QQ, VSCode, etc.) need the sandbox binary:

```bash
# Find chrome-sandbox
find / -name chrome-sandbox 2>/dev/null

# Fix ownership and suid
sudo chown root:root <path-to>/chrome-sandbox
sudo chmod 4755 <path-to>/chrome-sandbox
```

Verify sandbox is fixed by running the app; if it no longer crashes with "SUID sandbox helper" error, it worked.

### 9. Handle GPU incompatibility (DGX Spark / Blackwell GPU)

On **NVIDIA DGX Spark** (ARM64 + Blackwell GPU), old Electron apps that use Vulkan via `freedreno` driver may crash with:

```
VK_ERROR_INCOMPATIBLE_DRIVER
GPU process isn't usable. Goodbye.
```

Fix by launching with software rendering:

```bash
<binary> --disable-gpu
```

**Persist the fix in the desktop file** so the icon launcher works:

```bash
# Create/update user-level .desktop
cat > ~/.local/share/applications/<app>.desktop << 'EOF'
[Desktop Entry]
Version=<version>
Name=<中文名>
Exec=~/.local/opt/<AppDir>/<binary> --disable-gpu %U
Icon=~/.local/opt/<AppDir>/<icon>.png
Terminal=false
Type=Application
Categories=Application;Network;
StartupNotify=true
EOF

# Place on desktop (check desktop dir name — may be 桌面/ or Desktop/)
DESKTOP_DIR="$HOME/Desktop"
[ -d "$DESKTOP_DIR" ] || DESKTOP_DIR="$HOME/桌面"
cp ~/.local/share/applications/<app>.desktop "$DESKTOP_DIR"/<应用名>.desktop
chmod +x "$DESKTOP_DIR"/<应用名>.desktop
```

### 10. Refresh desktop menu

```bash
update-desktop-database ~/.local/share/applications/
```

## Single-Binary Release Install (no root)

Many tools ship only as a bare static binary attached to a GitHub Release. With no
passwordless `sudo`, install into `~/.local/bin` (confirm it is on PATH first):

```bash
mkdir -p ~/.local/bin
# GitHub direct frequently times out from mainland China — fetch through a mirror, then
# verify against the vendor's own index (below) before trusting the bytes.
curl -fL --retry 3 -o /tmp/<tool> "https://<mirror>/https://github.com/<org>/<repo>/releases/download/<tag>/<asset>"
chmod +x /tmp/<tool>
/tmp/<tool> --version          # proves right arch AND that it actually runs
mv /tmp/<tool> ~/.local/bin/<tool>
```

### Verify against the vendor's own index, not the mirror

A mirror is untrusted transport: use it to *fetch*, then confirm the artifact against the
vendor's authoritative package index. When the project also publishes an apt repo, that
repo carries the official digest:

```bash
curl -fsSL https://<vendor-apt>/dists/<suite>/main/binary-arm64/Packages | grep -A6 '^Package: <name>$'
sha256sum /tmp/<tool>
```

The strongest check is the vendor's own `.deb` — same bytes, second source:

```bash
curl -fL -o /tmp/p.deb https://<vendor-apt>/pool/main/<x>/<name>/<name>_<ver>_arm64.deb
dpkg-deb -x /tmp/p.deb /tmp/vendor && sha256sum /tmp/vendor/usr/bin/<name> /tmp/<tool>
```

- **Match the version on both sides before comparing hashes.** A checksum published for a
  *different* release will never match authentic bytes; the resulting mismatch looks like
  supply-chain tampering and sends you hunting a problem that does not exist. Confirm
  `<tool> --version` equals the version the checksum/index entry belongs to.
- If the vendor publishes no digest at all, say so plainly ("fetched via mirror, no upstream
  checksum available") rather than implying the download was verified.
- Clean up the probe directories afterwards; leave no stray `/tmp/<tool>-verify` trees.

## Pitfalls

- **RPM vs DEB on Ubuntu**: never `alien` if avoidable — `rpm2cpio + cpio` is faster and doesn't need full rpm/dpkg interop.
- **Old RPMs may be sandbox-incompatible** with newer Electron/Chromium versions. Check the app version before installing.
- **Always check if the user already has a newer version** installed first (`which <app>`, `~/.local/bin/`, `~/.local/opt/`). Don't downgrade them.
- **ARM64 ≠ AMD64 compatibility**: an x86_64 RPM won't run on ARM64 even with `--force-architecture`. Always verify the ELF header.
- **`apt update` zombie process**: if `apt-get install` fails with lock error, check `ps aux | grep apt` for stale processes before `kill` + retry.
- **Desktop directory name varies**: GNOME on Ubuntu uses `~/Desktop/` (English locale) or `~/桌面/` (Chinese locale). Check both; don't assume one.
- **GPU crash on DGX Spark**: Blackwell GPU via `freedreno` Vulkan driver is incompatible with old Electron (<v25). Always test `timeout 5 <binary>` first; if it crashes with `GPU process isn't usable`, add `--disable-gpu`. Persist in `.desktop` file, not just CLI.
- **Don't write to `/usr/share/applications/` unless the user has sudo and you verified the file doesn't exist**. Prefer `~/.local/share/applications/` for user-level apps — less permission trouble, survives system updates.

## Verification

After install, confirm the app appears in the desktop menu:
```bash
grep -r "<app>" /usr/share/applications/
```
