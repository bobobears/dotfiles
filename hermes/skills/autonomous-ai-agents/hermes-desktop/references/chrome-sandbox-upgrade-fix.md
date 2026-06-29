# Chrome Sandbox Breakage After Hermes Upgrade

## Original Diagnosis (session 2026-06-24)

The user upgraded Hermes Agent, then the desktop icon stopped responding on double-click.

### Diagnostic Steps

1. Located the desktop file: `~/Desktop/hermes-desktop.desktop`
2. Read the `Exec` line: `/home/bobobears/.hermes/hermes-agent/venv/bin/hermes desktop --skip-build`
3. Confirmed the `hermes` script existed at that path
4. Ran the command directly in terminal (reveals the hidden error):
   ```
   /home/bobobears/.hermes/hermes-agent/venv/bin/hermes desktop --skip-build 2>&1
   ```

### Error Output

```
→ Skipping desktop package build (--skip-build); using
  /home/bobobears/.hermes/hermes-agent/apps/desktop/release/linux-arm64-unpacked/Hermes
→ Configuring Electron Linux sandbox helper (sudo required)...
✗ Failed to configure Electron's Linux sandbox helper:
  /home/bobobears/.hermes/hermes-agent/apps/desktop/release/linux-arm64-unpacked/chrome-sandbox
```

### Root Cause

During `hermes update`, the release directory at `apps/desktop/release/` is replaced with a fresh build. The new `chrome-sandbox` binary has default permissions (`-rwxr-xr-x bobobears:bobobears` 17064 bytes) instead of the required SUID root (`-rwsr-xr-x root:root`).

When launched from the desktop (no terminal), `sudo` fails silently because there's no tty to read the password. The Electron app never starts.

### Fixed Permissions

```
-rwsr-xr-x 1 root root 17064  /path/to/chrome-sandbox
```

### Verification

After fix, `hermes desktop --skip-build` starts the Electron app with proper process tree:
- `hermes desktop --skip-build` (CLI wrapper)
- `Hermes` (Electron main process)
- `chrome-sandbox Hermes --type=zygote` (sandboxed subprocesses)
- Various `zygote`, `network`, `audio` utility processes
- `python -m hermes_cli.main dashboard` (backend dashboard)
