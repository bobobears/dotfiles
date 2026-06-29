# LM Studio Installation Example

Real-world installation of LM Studio 0.4.16+2 (ARM64) on Ubuntu 24.04 aarch64.

## File

```
LM-Studio-0.4.16-2-arm64.AppImage  (1.33 GB)
```

## Commands used

```bash
# Found in ~/下载/ (Chinese locale)
# Made executable
chmod +x ~/下载/LM-Studio-0.4.16-2-arm64.AppImage

# Copied to clean path
cp ~/下载/LM-Studio-0.4.16-2-arm64.AppImage ~/LM-Studio.AppImage

# Desktop entry written to:
#   ~/.local/share/applications/lm-studio.desktop
#   ~/Desktop/lm-studio.desktop
#
# Exec= line: /home/bobobears/LM-Studio.AppImage --no-sandbox

# Icon extracted via --appimage-extract
./LM-Studio.AppImage --appimage-extract
# Icon was at: squashfs-root/usr/share/icons/hicolor/0x0/apps/lm-studio.png
# Installed to: ~/.local/share/icons/hicolor/256x256/apps/lm-studio.png
```

## Verification

Running processes after launch:
```
/tmp/.mount_LM-Stut9gyf6/lm-studio --no-sandbox
```
