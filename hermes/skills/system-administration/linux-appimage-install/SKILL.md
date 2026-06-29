---
name: linux-appimage-install
description: Install, integrate, and create desktop shortcuts for AppImage applications on Linux.
---

# Linux AppImage Installation

Install AppImage applications with proper desktop integration — icons, menu entries, and desktop shortcuts.

## When to use

- User downloaded an `.AppImage` file and needs it installed properly
- User can't find the launch icon after running the AppImage
- User wants a proper application menu entry for an AppImage
- User wants a desktop shortcut for an AppImage

## Steps

### 1. Find the AppImage

The user may have it in a localized `~/下载/` (Chinese), `~/Downloads/`, or another location. Check the home directory:

```bash
find ~ -maxdepth 3 -name "*.AppImage" -type f 2>/dev/null
```

### 2. Make it executable

```bash
chmod +x /path/to/Application.AppImage
```

### 3. Copy to a clean location (avoid locale-sensitive paths)

Hermes tools may reject workdirs containing non-ASCII characters. Copy the AppImage to the home directory to keep paths clean:

```bash
cp /path/to/Application.AppImage ~/Application.AppImage
```

### 4. Create the `.desktop` file

Write to `~/.local/share/applications/` (app menu) and `~/Desktop/` (desktop shortcut):

```ini
[Desktop Entry]
Name=Application Name
Comment=Description of the app
Exec=/home/bobobears/Application.AppImage --no-sandbox
Icon=application-name
Type=Application
Categories=Development;Utility;
Terminal=false
StartupWMClass=application-name
```

Both files must be executable: `chmod +x ~/Desktop/application.desktop`

### 5. Extract and install the icon

Some AppImages have embedded icons. Extract them:

```bash
# Full extraction (a squashfs-root/ dir appears in cwd)
cd ~ && ./Application.AppImage --appimage-extract

# Find the icon(s)
find ~/squashfs-root/ -name "*.png" -path "*/icons/*" 2>/dev/null

# Install to user icon theme
mkdir -p ~/.local/share/icons/hicolor/256x256/apps
cp ~/squashfs-root/usr/share/icons/hicolor/<size>/apps/<name>.png \
   ~/.local/share/icons/hicolor/256x256/apps/<name>.png

# Clean up extracted files
rm -rf ~/squashfs-root
```

### 6. Update icon cache (optional)

```bash
gtk-update-icon-cache ~/.local/share/icons/hicolor/ 2>/dev/null || true
update-desktop-database ~/.local/share/applications/ 2>/dev/null || true
```

## Pitfalls

- **Chinese-character paths**: Hermes terminal's `workdir` parameter rejects non-ASCII characters. Always copy the AppImage to a simple ASCII path before running it.
- **`--no-sandbox` flag**: Many Electron-based AppImages (like LM Studio) require `--no-sandbox` on Linux. Include it in the `Exec=` line of the `.desktop` file.
- **AppImage mount cleanup**: AppImages auto-mount under `/tmp/.mount_<Name><hash>/`. This directory disappears when the app exits, so extract icons *before* closing the app or use `--appimage-extract` on the file directly.
- **Desktop envirionment**: Some desktop environments (GNOME, KDE) may need a logout/login before new `.desktop` entries appear in the app menu.
- **Icon size**: If `0x0` is the only icon size in the AppImage (common in Electron apps), install it under `256x256` — it scales fine.
