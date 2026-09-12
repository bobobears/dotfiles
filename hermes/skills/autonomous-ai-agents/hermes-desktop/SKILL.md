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

### Desktop stuck on "An update is finishing" (init screen forever)

**Symptom:** After an upgrade, Desktop opens but stays on the init screen showing `An update is finishing — Hermes will start automatically when it completes…` indefinitely. `desktop.log` repeats this line; the app never completes startup.

**Root cause:** The `posix.sh` update hand-off script runs `hermes update --yes --gateway`. The update's last step requests a gateway restart, but the gateway defers it while active work units (e.g. a Feishu/WeChat turn) are running — it waits up to ~6h (`cap=21600s`, see `Restart deferred: waiting on N active work unit(s)` in `gateway.log`). `hermes update` blocks on that, so the update marker `~/.hermes/.hermes-update-in-progress` never gets cleared, and any new Desktop boot sees the marker and parks on the init screen. The code/git update itself usually finished long ago.

**Diagnosis:**
```bash
# 1. Stale update processes still alive?
ps aux | grep -E "desktop-update/posix.sh|hermes update --yes"
# 2. Marker present?
cat ~/.hermes/.hermes-update-in-progress
# 3. Gateway deferring restart?
grep "Restart deferred" ~/.hermes/logs/gateway.log | tail -3
# 4. Update itself completed?
tail -20 ~/.hermes/logs/desktop-update-handoff.log   # "hermes update exit code: 0" = done
```

**Fix (update already completed case):**
```bash
# Kill the stuck update chain (posix.sh + its hermes update child)
pkill -f "desktop-update/posix.sh"; pkill -f "hermes update --yes"
# Clear the marker and stale result so Desktop boot no longer waits
rm -f ~/.hermes/.hermes-update-in-progress ~/.hermes/.hermes-update-result.json
# Fix chrome-sandbox (upgrade usually resets it too) — see chrome-sandbox section
# Then relaunch Desktop
~/.hermes/hermes-agent/venv/bin/hermes desktop --skip-build
```

Verify the marker is gone and the Desktop log proceeds past `An update is finishing` to `Hermes backend is ready. Finalizing desktop startup`.

**Pitfall:** If the stuck `hermes update` process is still mid-flight (git pull actively running), killing it can leave a half-applied update — re-run `hermes update` from a terminal afterward. In the common case (git log already at the new commit, build dir fresh) it is safe to kill.

### China-network variant (cua-driver download hang): On mainland China networks the post-update step may hang downloading `https://raw.githubusercontent.com/trycua/cua/main/libs/cua-driver/scripts/install.sh` (curl child under `hermes update`, 0-byte file in `/tmp/cua-driver-install-*.sh`). The git update itself already completed — the hang is only the cua-driver reinstall, which usually already exists at `~/.local/bin/cua-driver`. Diagnosis: `ps -ef --forest | grep -E "hermes update"` shows a `curl -fsSL -o /tmp/cua-driver-install-*.sh` child; the script file is 0 bytes. Safe to kill the whole chain (`pkill -f "desktop-update/posix.sh"; pkill -f "hermes update --yes"`; kill any surviving python child by PID), clear the markers, fix chrome-sandbox, and relaunch. Desktop runs fine without re-running the cua-driver install; only the computer-use feature needs it.

**Newer variant (cua-driver-rs release tarball):** The hang can also occur one step deeper — after `install.sh` downloads fine, its `_install-rust.sh` helper curls the release tarball from `https://github.com/trycua/cua/releases/download/cua-driver-rs-v*/...-linux-arm64-binary.tar.gz`. Diagnosis: a curl child writing to `/tmp/tmp.*/cua-driver-rs-*-binary.tar.gz.partial` that grows at ~200KB/min (GitHub is throttled on CN networks). Same treatment: kill the chain by exact PIDs (`ps -ef --forest | grep "hermes update"` — note `pkill -f` can match and kill your own shell if its command line contains the same pattern), clear markers, relaunch. The existing cua-driver (even an older version) keeps working; only re-upgrade it later via a mirror. As of 2026-08: `ghproxy.com` and `mirror.ghproxy.com` time out from CN networks — use `https://ghfast.top/` prefix instead (verified ~45s for the 27MB tarball). Manual install layout: extract to `~/.cua-driver/packages/releases/<ver>-aarch64-unknown-linux-gnu/`, then atomic-swap the `current` symlink (`ln -s ... .tmp && mv -Tf .tmp current`); remove any stale `.install.lock.d` left by a killed installer first.

**No-sudo fallback for chrome-sandbox:** If `sudo chown/chmod` is unavailable (password prompt in headless/CLI context), the SUID fix can be skipped entirely: when `/proc/sys/kernel/apparmor_restrict_unprivileged_userns` is `1`, launching via CLI (`hermes desktop --skip-build`) auto-detects it and appends `--no-sandbox` to the Electron launch (see `_desktop_linux_needs_no_sandbox()` in hermes_cli/main.py). Desktop boots fine on that path; only double-clicking the .desktop icon would hit the sandbox failure, so update the launcher's Exec line with ` --no-sandbox` if needed.

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

### Missing `desktop-plugins` directory

**Symptom:** Desktop launches but Electron main process repeatedly logs:
```
Error occurred in handler for 'hermes:watchDirectory': Error: Not a directory: /home/you/.hermes/desktop-plugins
```

**Root cause:** The `~/.hermes/desktop-plugins` directory is expected by the Electron main process but not always created during install or upgrade.

**Fix:**
```bash
mkdir -p ~/.hermes/desktop-plugins
```
Then restart the desktop app.

### HTTP 400: Model name mismatch (Provider X doesn't accept model Y)

**Symptom:** Desktop window opens, backend starts, but every API call fails with:
```
HTTP 400: The supported API model names are deepseek-v4-pro or deepseek-v4-flash, but you passed qwen/qwen3.6-27b.
```

**Root cause:** Desktop's internal `hermes serve` backend resolves the provider and model independently. When `model.provider` (e.g. `lmstudio`) differs from `delegation.provider` (e.g. `deepseek`), the serve backend can route to the wrong provider endpoint while keeping the original model name, causing a 400 because the target API doesn't recognize it.

**Diagnosis:**
```bash
grep 'Provider:' ~/.hermes/logs/desktop.log | tail -5
# Look for mismatched provider + model pairs
```

**Fix:** Ensure `model.provider`, `model.default`, and `model.base_url` are all consistent. See `references/model-routing-mismatch.md` for full error transcripts and resolution steps.

### Missing desktop-plugins directory

**Symptom:** Desktop launches but Electron main process logs `Error: Not a directory: /home/you/.hermes/desktop-plugins` in `~/.hermes/logs/desktop.log`. May cause watchDirectory failures or plugin loading errors.

**Root cause:** The `~/.hermes/desktop-plugins` directory is expected by the Electron main process but not always created during installation or upgrade.

**Fix:**
```bash
mkdir -p ~/.hermes/desktop-plugins
```

Then restart the desktop app.

### HTTP 400: Model name mismatch (Provider X doesn't accept model Y)

**Symptom:** Desktop launches, backend starts, but every API call fails with:
```
HTTP 400: The supported API model names are deepseek-v4-pro or deepseek-v4-flash, but you passed qwen/qwen3.6-27b.
```
Log shows `Provider: deepseek  Model: qwen/qwen3.6-27b` — provider and model name are from different sources.

**Root cause:** Desktop's internal `hermes serve` backend resolves the provider and model independently. If `config.yaml` has `model.provider` set to one provider (e.g., `lmstudio`) but `delegation.provider` set to another (e.g., `deepseek`), the serve backend can use the wrong provider endpoint while keeping the original model name. This results in a 400 error because the target API doesn't recognize the model name.

**Diagnosis:**
```bash
# Check what the desktop backend actually uses:
grep 'Provider:' ~/.hermes/logs/desktop.log | tail -5
# Should show the same provider and model that match each other
```

**Fix:** Ensure `model.provider`, `model.default`, and `model.base_url` are consistent. Either:
1. Set all to the same provider/model:
   ```bash
   hermes config set model.provider deepseek
   hermes config set model.default deepseek-v4-flash
   hermes config set model.base_url https://api.deepseek.com/v1
   ```
2. Or set all to LM Studio:
   ```bash
   hermes config set model.provider lmstudio
   hermes config set model.default qwen/qwen3.6-27b
   hermes config set model.base_url http://127.0.0.1:1234/v1
   ```

After fixing, restart the desktop app. See `references/model-routing-mismatch.md` for detailed error transcripts and resolution.

## Important Paths

| Asset | Path |
|-------|------|
| Venv command | `~/.hermes/hermes-agent/venv/bin/hermes` |
| Desktop launcher | `~/Desktop/hermes-desktop.desktop` |
| Electron release | `~/.hermes/hermes-agent/apps/desktop/release/linux-*-unpacked/` |
| Chrome sandbox | `.../release/linux-arm64-unpacked/chrome-sandbox` |
| Desktop app icon | `~/.hermes/hermes-agent/apps/desktop/assets/icon.png` |
| User config | `~/.config/Hermes/` (Electron app data) |
| Desktop log | `~/.hermes/logs/desktop.log` |
| Desktop plugins | `~/.hermes/desktop-plugins/` |
| Desktop log | `~/.hermes/logs/desktop.log` |
| Desktop plugins | `~/.hermes/desktop-plugins/` |
