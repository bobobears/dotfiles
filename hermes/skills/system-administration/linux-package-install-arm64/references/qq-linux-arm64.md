# QQ Linux on ARM64 — Installation & GPU Fix Reference

## Context

- **System**: Ubuntu 24.04 LTS, **NVIDIA DGX Spark** (ARM64 / aarch64, Blackwell GPU)
- **App version**: QQ for Linux v3.2.29 (Electron-based, self-contained under `~/.local/opt/QQ/`)
- **Install source**: Pre-installed via a standard method (symlink at `~/.local/bin/qq` → `~/.local/opt/QQ/qq`)

## Observed Issues & Fixes

### Issue 1: chrome-sandbox SUID permission

```
The SUID sandbox helper binary was found, but is not configured correctly.
Rather than run without sandboxing I'm aborting now.
You need to make sure that .../chrome-sandbox is owned by root and has mode 4755.
```

**Fix:**
```bash
sudo chown root:root ~/.local/opt/QQ/chrome-sandbox
sudo chmod 4755 ~/.local/opt/QQ/chrome-sandbox
```

### Issue 2: GPU incompatibility (Blackwell + freedreno Vulkan)

```
TU: error: ../src/freedreno/vulkan/tu_knl.cc:387: failed to open device /dev/dri/renderD128
GPU process isn't usable. Goodbye.
```

The NVIDIA DGX Spark's Blackwell GPU uses the `freedreno` Vulkan driver, which is incompatible with the old Chromium/Electron version shipped in QQ v3.2.29.

**Fix:** Disable GPU in Electron:
```bash
qq --disable-gpu
```

### Issue 3: Desktop launcher with GPU fix

Create a user `~/.local/share/applications/qq.desktop` with `--disable-gpu` baked in, then copy to desktop:

```bash
DESKTOP_DIR="$HOME/Desktop"
[ -d "$DESKTOP_DIR" ] || DESKTOP_DIR="$HOME/桌面"
cp ~/.local/share/applications/qq.desktop "$DESKTOP_DIR/腾讯QQ.desktop"
chmod +x "$DESKTOP_DIR/腾讯QQ.desktop"
```

.qows desktop file content:
```
[Desktop Entry]
Version=3.2.29
Name=腾讯QQ
Exec=/home/bobobears/.local/opt/QQ/qq --disable-gpu %U
Icon=/home/bobobears/.local/opt/QQ/QQ.png
Terminal=false
Type=Application
Categories=Application;Network;
```

## Lessons

- **Desktop directory name**: Check both `~/Desktop/` and `~/桌面/` — GNOME locale-dependent.
- **Icon location**: QQ's icon was not in the standard locations; extracted a PNG from the old RPM package and placed it next to the binary.
- **Session note**: The user also had an old v2.0.0 RPM in `~/下载/` — always check existing installs before proceeding.
