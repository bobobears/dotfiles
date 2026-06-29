---
name: ubuntu-gnome-makeover
description: "One-command script to apply the full GNOME desktop makeover: Papirus icons, Orchis GTK/Shell theme, Bibata cursor, Ubuntu font, Desktop Icons NG, and Ubuntu Dock tuning. Safe for Ubuntu 24.04 LTS GNOME 46."
---

# Ubuntu GNOME Desktop Makeover

一键应用全面 GNOME 桌面美化：图标、主题、指针、字体、Dock、桌面图标。

## 适用环境

- Ubuntu 24.04 LTS (Noble) — GNOME Shell 46
- 其他 Ubuntu 版本可能也兼容（包名可能不同）

## 一键恢复脚本

```bash
#!/bin/bash
set -e

echo "=========================================="
echo "   🎨 Ubuntu GNOME 桌面美化安装脚本"
echo "=========================================="

# 1. 安装必要包
sudo apt update
sudo apt install -y \
  papirus-icon-theme \
  orchis-gtk-theme \
  bibata-cursor-theme \
  fonts-noto-color-emoji

# 2. 启用 GNOME 扩展（通过 dconf 写入，无需运行 GNOME Shell）
dconf write /org/gnome/shell/enabled-extensions "['user-theme@gnome-shell-extensions.gcampax.github.com', 'ding@rastersoft.com', 'ubuntu-dock@ubuntu.com', 'ubuntu-appindicators@ubuntu.com']"

# 3. 应用主题
gsettings set org.gnome.desktop.interface icon-theme "Papirus-Dark"
gsettings set org.gnome.desktop.interface gtk-theme "Orchis-Dark"
gsettings set org.gnome.desktop.wm.preferences theme "Orchis-Dark"
gsettings set org.gnome.shell.extensions.user-theme name "Orchis-Dark"

# 4. 鼠标指针
gsettings set org.gnome.desktop.interface cursor-theme "Bibata-Modern-Classic"
gsettings set org.gnome.desktop.interface cursor-size 24

# 5. 字体
gsettings set org.gnome.desktop.interface font-name "Ubuntu 11"
gsettings set org.gnome.desktop.interface document-font-name "Ubuntu 11"
gsettings set org.gnome.desktop.interface font-antialiasing "rgba"
gsettings set org.gnome.desktop.interface font-hinting "slight"
gsettings set org.gnome.desktop.interface text-scaling-factor 1.0

# 6. Dock 配置
gsettings set org.gnome.shell.extensions.dash-to-dock dash-max-icon-size 40
gsettings set org.gnome.shell.extensions.dash-to-dock dock-position "BOTTOM"
gsettings set org.gnome.shell.extensions.dash-to-dock autohide false
gsettings set org.gnome.shell.extensions.dash-to-dock intellihide false
gsettings set org.gnome.shell.extensions.dash-to-dock extend-height true
gsettings set org.gnome.shell.extensions.dash-to-dock transparency-mode "FIXED"
gsettings set org.gnome.shell.extensions.dash-to-dock background-opacity 0.5

# 7. 桌面图标 (Desktop Icons NG)
gsettings set org.gnome.desktop.background show-desktop-icons true
dconf write /org/gnome/shell/extensions/ding/show-home false
dconf write /org/gnome/shell/extensions/ding/icon-size "'standard'"
dconf write /org/gnome/shell/extensions/ding/arrange-var "'top-left'"

echo ""
echo "=========================================="
echo "   ✅ 全部配置已写入！"
echo "=========================================="
echo "请重新登录或重启 GNOME Shell (Alt+F2 → r) 生效"
```

## 手动验证命令

```bash
# 查看所有已安装的图标主题
find /usr/share/icons -maxdepth 1 -type d | sort

# 查看当前主题设置
gsettings get org.gnome.desktop.interface icon-theme
gsettings get org.gnome.desktop.interface gtk-theme
gsettings get org.gnome.desktop.interface cursor-theme
gsettings get org.gnome.desktop.interface font-name

# 查看已启用的扩展
gnome-extensions list --enabled 2>/dev/null || echo "需要 GNOME Shell 会话"
```

## 主题切换小贴士

### Papirus 配色变体
- `Papirus` — 浅色模式
- `Papirus-Dark` — 深色模式（推荐）
- `Papirus-Light` — 高对比度浅色

### Orchis 配色变体
格式: `Orchis-{Color}-{Variant}`
- 颜色: Green, Grey, Orange, Pink, Purple, Red, Teal, Yellow 或不指定（默认蓝色）
- 变体: Dark, Light, 或不指定（浅色）
- 紧凑版: 加 -Compact 后缀
- 例: `Orchis-Teal-Dark`, `Orchis-Pink-Light-Compact`

### Bibata 光标变体
- `Bibata-Modern-Classic` — 现代经典黑
- `Bibata-Modern-Ice` — 现代冰雪蓝
- `Bibata-Modern-Amber` — 现代琥珀橙
- `Bibata-Original-Classic` — 原版经典黑
- `Bibata-Original-Ice` — 原版冰雪蓝
- `Bibata-Original-Amber` — 原版琥珀橙

## 自定义桌面图标

### ⚠️ 重要: GNOME 45+ 右键→属性改图标的行为已改变

**GNOME 45 及更高版本**（包括 Ubuntu 24.04 的 GNOME 46）中，在文件管理器右键文件→属性→点击图标，**只能添加徽标（emblem）**——图标右下角出现一个小标记，**图标本身不会改变**。这不是 bug，是 GNOME 的设计变更。

### 正确方法一：命令行替换文件夹图标（推荐）

```bash
# 把文件夹图标彻底换成自定义图片
gio set ~/Desktop/你的文件夹 metadata::custom-icon "file:///home/bobobears/图片/your-icon.png"

# 恢复默认图标
gio set ~/Desktop/你的文件夹 metadata::custom-icon ""
```

支持 PNG、SVG、JPG 格式。建议用 256×256 或 512×512 的 PNG/SVG。

### 正确方法二：用 .desktop 启动器替换脚本/程序图标

对于 `.sh` 脚本或二进制文件，`gio set` 的 `metadata::custom-icon` 不一定生效（Desktop Icons NG 对普通文件的支持有限）。**更可靠的做法是创建 `.desktop` 启动器：**

```bash
# 创建启动器文件
cat > ~/Desktop/MyLauncher.desktop << 'EOF'
[Desktop Entry]
Name=我的启动器
Comment=说明文字
Exec=bash /path/to/script.sh
Icon=/home/bobobears/图标/my-icon.png
Type=Application
Categories=System;Utility;
Terminal=true
StartupNotify=true
EOF

chmod +x ~/Desktop/MyLauncher.desktop
```

- `.desktop` 文件的 `Icon=` 字段支持绝对路径或系统图标主题名称
- 设置 `Terminal=true` 会让脚本在终端窗口中运行
- 刷新桌面: `Alt+F2` → `r` → 回车

### 自定义图标风格指南：匹配 Hermes + LM Studio 风格

Hermes Desktop 和 LM Studio 的图标共同特征：
- **圆角方形徽章**（squircle badge）：大圆角，约 220/1024 半径
- **扁平现代**：无阴影渐变，简明图形
- **深色背景 + 浅色图形**
- **尺寸**：1024×1024 RGBA PNG

用 Python PIL 生成匹配风格的自定义图标示例（详见 references/icon-creation.md）。

## 回滚方法

```bash
# 恢复为默认 Adwaita 主题
gsettings set org.gnome.desktop.interface icon-theme "Adwaita"
gsettings set org.gnome.desktop.interface gtk-theme "Adwaita"
gsettings set org.gnome.desktop.wm.preferences theme "Adwaita"
gsettings set org.gnome.shell.extensions.user-theme name ""
gsettings set org.gnome.desktop.interface cursor-theme "Adwaita"
gsettings set org.gnome.desktop.interface font-name "Cantarell 11"
gsettings set org.gnome.desktop.interface font-antialiasing "grayscale"
gsettings set org.gnome.desktop.interface font-hinting "none"

# 卸载包
sudo apt remove --purge papirus-icon-theme orchis-gtk-theme bibata-cursor-theme
```
