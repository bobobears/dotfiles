#!/usr/bin/env bash
# gnome-desktop-theming: quick-setup script
# Installs and applies the recommended GNOME desktop theming stack.
# Run: bash scripts/quick-setup.sh
# Safe to re-run — idempotent via apt + gsettings.

set -euo pipefail

echo "=== GNOME Desktop Theming — Quick Setup ==="
echo ""

# --- Install packages ---
echo "[1/5] Installing theme packages..."
sudo apt install -y \
  papirus-icon-theme \
  orchis-gtk-theme \
  bibata-cursor-theme \
  fonts-noto-color-emoji \
  2>&1 | grep -E "(升级|安装|已经是)" || true

# --- Apply icon theme ---
echo "[2/5] Applying icon theme (Papirus-Dark)..."
gsettings set org.gnome.desktop.interface icon-theme "Papirus-Dark" 2>/dev/null || true

# --- Apply GTK/Shell theme ---
echo "[3/5] Applying GTK/Shell theme (Orchis-Dark)..."
gsettings set org.gnome.desktop.interface gtk-theme "Orchis-Dark" 2>/dev/null || true
gsettings set org.gnome.desktop.wm.preferences theme "Orchis-Dark" 2>/dev/null || true
gsettings set org.gnome.shell.extensions.user-theme name "Orchis-Dark" 2>/dev/null || true

# --- Apply cursor theme ---
echo "[4/5] Applying cursor theme (Bibata-Modern-Classic)..."
gsettings set org.gnome.desktop.interface cursor-theme "Bibata-Modern-Classic" 2>/dev/null || true
gsettings set org.gnome.desktop.interface cursor-size 24 2>/dev/null || true

# --- Font & rendering ---
echo "[5/5] Optimizing font rendering..."
gsettings set org.gnome.desktop.interface font-name "Ubuntu 11" 2>/dev/null || true
gsettings set org.gnome.desktop.interface document-font-name "Ubuntu 11" 2>/dev/null || true
gsettings set org.gnome.desktop.interface font-antialiasing "rgba" 2>/dev/null || true
gsettings set org.gnome.desktop.interface font-hinting "slight" 2>/dev/null || true

# --- Enable extensions via dconf (works even without running GNOME Shell) ---
echo ""
echo "Enabling GNOME extensions..."
dconf write /org/gnome/shell/enabled-extensions "['user-theme@gnome-shell-extensions.gcampax.github.com', 'ding@rastersoft.com', 'ubuntu-dock@ubuntu.com', 'ubuntu-appindicators@ubuntu.com']" 2>/dev/null || true

# --- Dock config ---
echo "Configuring Dock..."
gsettings set org.gnome.shell.extensions.dash-to-dock dash-max-icon-size 40 2>/dev/null || true
gsettings set org.gnome.shell.extensions.dash-to-dock dock-position "BOTTOM" 2>/dev/null || true
gsettings set org.gnome.shell.extensions.dash-to-dock autohide false 2>/dev/null || true
gsettings set org.gnome.shell.extensions.dash-to-dock extend-height true 2>/dev/null || true

# --- Desktop Icons NG ---
echo "Configuring Desktop Icons..."
gsettings set org.gnome.desktop.background show-desktop-icons true 2>/dev/null || true
dconf write /org/gnome/shell/extensions/ding/show-home false 2>/dev/null || true

echo ""
echo "========================================"
echo "  ✅  Setup complete!"
echo "========================================"
echo ""
echo "Current settings:"
echo "  Icon:     $(gsettings get org.gnome.desktop.interface icon-theme 2>/dev/null)"
echo "  GTK:      $(gsettings get org.gnome.desktop.interface gtk-theme 2>/dev/null)"
echo "  Cursor:   $(gsettings get org.gnome.desktop.interface cursor-theme 2>/dev/null)"
echo "  Font:     $(gsettings get org.gnome.desktop.interface font-name 2>/dev/null)"
echo ""
echo "Restart GNOME Shell (Alt+F2 → r → Enter) or log out/in to see all changes."
