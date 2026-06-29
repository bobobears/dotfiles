---
name: hermes-desktop
description: "Troubleshoot, configure, and maintain the Hermes Desktop Electron application — startup issues, desktop icon, chrome-sandbox permissions, and upgrade recovery."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, desktop, electron, sandbox, troubleshooting, upgrade]
    related_skills: [hermes-agent]
---

# Hermes Desktop

Hermes Desktop is the Electron-based GUI application for Hermes Agent, launched via `hermes desktop --skip-build`. It provides a graphical interface for interacting with Hermes alongside the CLI and messaging gateway.

**This skill covers** desktop-specific setup, startup troubleshooting, sandbox configuration, and recovery after upgrades.

## Desktop Entry (.desktop file)

Hermes creates a desktop launcher at `~/Desktop/hermes-desktop.desktop` during setup. The typical content:

```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=Hermes Desktop
Exec=/home/you/.hermes/hermes-agent/venv/bin/hermes desktop --skip-build
Path=/home/you/.hermes/hermes-agent
Icon=/home/you/.hermes/hermes-agent/apps/desktop/assets/icon.png
Terminal=false
StartupNotify=true
Categories=Utility;Development;
```

The desktop entry runs inside the Hermes venv and uses `--skip-build` to avoid rebuilding the Electron application on every launch.

## Common Troubleshooting

### Double-click desktop icon does nothing (silent failure)

**Symptom:** After `hermes update` (or Hermes upgrade), double-clicking the desktop icon shows no window, no error, nothing.

**Root cause:** The upgrade replaces `apps/desktop/release/linux-arm64-unpacked/chrome-sandbox` with a new binary that lacks the SUID root permission. Electron requires `chrome-sandbox` to be SUID root for namespace isolation. When launched from the desktop, there is no terminal to prompt for the `sudo` password, so the sandbox configuration silently fails.

**Fix:**
```bash
cd ~/.hermes/hermes-agent/apps/desktop/release/linux-arm64-unpacked
sudo chown root:root chrome-sandbox
sudo chmod 4755 chrome-sandbox
```

**Verification:** The correct permissions are `-rwsr-xr-x root root`.

```bash
ls -la chrome-sandbox  # should show -rwsr-xr-x root ...
```

After fixing, double-click the desktop icon or run:
```bash
~/Desktop/hermes-desktop.desktop
# or directly:
~/.hermes/hermes-agent/venv/bin/hermes desktop --skip-build
```

### Command-line diagnosis

To see the actual error (bypasses the silent-fail path from desktop launch):

```bash
~/.hermes/hermes-agent/venv/bin/hermes desktop --skip-build 2>&1
```

If the sandbox is the issue, output looks like:
```
→ Skipping desktop package build (--skip-build); using .../Hermes
→ Configuring Electron Linux sandbox helper (sudo required)...
✗ Failed to configure Electron's Linux sandbox helper: .../chrome-sandbox
```

### Desktop app doesn't start at all (no sandbox error)

Check:
1. The venv still works: `~/.hermes/hermes-agent/venv/bin/hermes --version`
2. The release exists: `ls ~/.hermes/hermes-agent/apps/desktop/release/linux-*/`
3. The desktop file path is correct: `grep Exec ~/Desktop/hermes-desktop.desktop`

If the release directory was deleted during upgrade, run without `--skip-build`:
```bash
~/.hermes/hermes-agent/venv/bin/hermes desktop
```
This rebuilds the Electron app if needed (may take 30–90s on first build).

## Important Paths

| Asset | Path |
|-------|------|
| Venv command | `~/.hermes/hermes-agent/venv/bin/hermes` |
| Desktop launcher | `~/Desktop/hermes-desktop.desktop` |
| Electron release | `~/.hermes/hermes-agent/apps/desktop/release/linux-*-unpacked/` |
| Chrome sandbox | `.../release/linux-*-unpacked/chrome-sandbox` |
| Desktop app icon | `~/.hermes/hermes-agent/apps/desktop/assets/icon.png` |
| User config | `~/.config/Hermes/` (Electron app data) |
