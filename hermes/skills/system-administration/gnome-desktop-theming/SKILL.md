---
name: gnome-desktop-theming
description: "Ubuntu/GNOME 桌面美化 — 图标/GTK/Shell 主题、鼠标指针、字体渲染、Dock 配置、桌面图标扩展、GNOME Shell 扩展管理。覆盖 Ubuntu 24.04+ (GNOME 46+)。"
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [gnome, desktop, theming, ubuntu, linux, customization, icons, gtk, fonts, dock]
    related_skills: [linux-appimage-install]
---

# GNOME Desktop Theming Skill（GNOME 桌面美化）

## 概述

对 Ubuntu 24.04+ (GNOME 46+) 进行完整的桌面视觉优化。涵盖：

- 图标主题（Papirus、Tela Circle、McMojave 等）
- GTK/Shell 主题（Orchis、Materia 等）
- 鼠标指针主题（Bibata、phinger 等）
- 字体渲染优化（抗锯齿、微调、缩放）
- Ubuntu Dock 配置（大小、位置、透明度）
- Desktop Icons NG 桌面图标管理
- GNOME Shell 扩展的启用/配置
- Emoji 字体支持（Noto Color Emoji）

## 触发条件

- 用户要求"美化桌面"、"换主题"、"换图标"、"优化显示"
- 用户问"怎么让 Ubuntu 看起来更好看"
- 用户提到 Papirus、Orchis、Yaru、Bibata 等主题名称
- 用户抱怨图标/字体/桌面外观不好看
- 用户问"GNOME 扩展"、"Dock 设置"、"桌面图标"

## 前置条件

```bash
# 必要的工具（通常已预装）
sudo apt install -y gnome-tweaks gnome-shell-extension-prefs
```

## 核心工作流

### 第 1 步：诊断当前状态

收集系统信息和当前设置，为后续决策提供依据：

```bash
# 系统版本和桌面环境
lsb_release -a
gnome-shell --version
echo $XDG_CURRENT_DESKTOP

# 当前主题设置
gsettings get org.gnome.desktop.interface icon-theme
gsettings get org.gnome.desktop.interface gtk-theme
gsettings get org.gnome.desktop.wm.preferences theme
gsettings get org.gnome.desktop.interface cursor-theme

# 字体设置
gsettings get org.gnome.desktop.interface font-name
gsettings get org.gnome.desktop.interface text-scaling-factor
gsettings get org.gnome.desktop.interface font-antialiasing
gsettings get org.gnome.desktop.interface font-hinting

# 已安装的扩展
ls /usr/share/gnome-shell/extensions/
ls ~/.local/share/gnome-shell/extensions/ 2>/dev/null

# 启用的扩展
gnome-extensions list --enabled 2>/dev/null || echo "GNOME Shell not running — use dconf instead"

# 已安装的主题/图标
find /usr/share/icons ~/.local/share/icons ~/.icons -maxdepth 1 -type d 2>/dev/null | sort
find /usr/share/themes ~/.local/share/themes ~/.themes -maxdepth 1 -type d 2>/dev/null | sort

# Dock 设置
gsettings get org.gnome.shell.extensions.dash-to-dock dash-max-icon-size 2>/dev/null
gsettings get org.gnome.shell.extensions.ubuntu-dock dash-max-icon-size 2>/dev/null
```

### 第 2 步：向用户展示主题选项

使用 `references/theme-catalog.md` 中的主题清单，向用户展示各主题的风格和效果预览链接，让用户选择方向。

- 如果用户明确说出想装的名称 → 直接安装
- 如果用户犹豫 → 展示对比，询问偏好（换图标 vs 整体美化）
- 用户偏好中文交互时用中文描述选项

### 第 3 步：安装所选主题

**图标主题**（从 references/theme-catalog.md 选取）：

```bash
# Papirus（最流行，推荐）
sudo apt install -y papirus-icon-theme
gsettings set org.gnome.desktop.interface icon-theme "Papirus-Dark"

# 其他主题通过 git clone + install.sh 安装
# git clone 时用户可能在受限网络环境，注意使用镜像
```

**GTK/Shell 主题**：

```bash
# Orchis（推荐，apt 直接安装）
sudo apt install -y orchis-gtk-theme
gsettings set org.gnome.desktop.interface gtk-theme "Orchis-Dark"
gsettings set org.gnome.desktop.wm.preferences theme "Orchis-Dark"
```

**鼠标指针主题**：

```bash
# Bibata（推荐）
sudo apt install -y bibata-cursor-theme
gsettings set org.gnome.desktop.interface cursor-theme "Bibata-Modern-Classic"
gsettings set org.gnome.desktop.interface cursor-size 24
```

**Emoji 字体**：

```bash
sudo apt install -y fonts-noto-color-emoji
```

### 第 4 步：启用并配置 GNOME 扩展

当 `gnome-extensions enable` 失败时（GNOME Shell 未运行），使用 dconf 直接写入：

```bash
# 方法 A：通过 gnome-extensions（需要运行中的 GNOME Shell）
gnome-extensions enable user-theme@gnome-shell-extensions.gcampax.github.com
gnome-extensions enable ding@rastersoft.com
gnome-extensions enable ubuntu-dock@ubuntu.com

# 方法 B：通过 dconf（通用，不管 GNOME Shell 是否在运行）
dconf write /org/gnome/shell/enabled-extensions "['user-theme@gnome-shell-extensions.gcampax.github.com', 'ding@rastersoft.com', 'ubuntu-dock@ubuntu.com', 'ubuntu-appindicators@ubuntu.com']"
```

⚠️ **dconf 写入时需要注意**：扩展 UUID 列表必须用 `['...', '...']` 格式（单引号外套双引号）。

### 第 5 步：Shell 主题应用

```bash
# 先确保 user-theme 扩展已启用
gsettings set org.gnome.shell.extensions.user-theme name "Orchis-Dark"
# 或者通过 dconf（当 gsettings 不可用时）
dconf write /org/gnome/shell/extensions/user-theme/name "'Orchis-Dark'"
```

### 第 6 步：Dock 配置

```bash
# 图标大小
gsettings set org.gnome.shell.extensions.dash-to-dock dash-max-icon-size 40

# 位置
gsettings set org.gnome.shell.extensions.dash-to-dock dock-position "BOTTOM"

# 自动隐藏
gsettings set org.gnome.shell.extensions.dash-to-dock autohide false
gsettings set org.gnome.shell.extensions.dash-to-dock intellihide false

# 高度
gsettings set org.gnome.shell.extensions.dash-to-dock extend-height true

# 透明度
gsettings set org.gnome.shell.extensions.dash-to-dock transparency-mode "FIXED"
gsettings set org.gnome.shell.extensions.dash-to-dock background-opacity 0.5
```

### 第 7 步：桌面图标配置

```bash
# Desktop Icons NG
gsettings set org.gnome.desktop.background show-desktop-icons true
dconf write /org/gnome/shell/extensions/ding/show-home false
dconf write /org/gnome/shell/extensions/ding/icon-size "'standard'"
dconf write /org/gnome/shell/extensions/ding/arrange-var "'top-left'"
```

### 第 8 步：字体渲染优化

```bash
# 使用 Ubuntu 字体替代默认 Cantarell（更清晰）
gsettings set org.gnome.desktop.interface font-name "Ubuntu 11"
gsettings set org.gnome.desktop.interface document-font-name "Ubuntu 11"
gsettings set org.gnome.desktop.interface monospace-font-name "Ubuntu Sans Mono 13"

# 抗锯齿和微调
gsettings set org.gnome.desktop.interface font-antialiasing "rgba"
gsettings set org.gnome.desktop.interface font-hinting "slight"

# 缩放（1.0 = 正常，1.05-1.1 = 稍大）
gsettings set org.gnome.desktop.interface text-scaling-factor 1.0
```

### 第 9 步：通知用户生效方式

所有配置通过 gsettings/dconf 即时写入，但 GNOME Shell 需要重启才能完全生效：

> **按 `Alt+F2` → 输入 `r` → 回车** 重启 Shell
> 或者直接 **注销重新登录**

## 常见陷阱

1. **gnome-extensions 报错 "连接 GNOME Shell 失败"**
   - 说明当前终端不在 GNOME Shell 会话中
   - **解决方法**：改用 dconf 写入，见第 4 步方法 B
   - dconf 写入的扩展列表在下次登录时生效

2. **apt 安装时锁占用 "无法获得锁 /var/lib/apt/lists/lock"**
   - 系统有后台 apt 进程（自动更新）
   - 可以等待它完成，或 `sudo kill -9 <pid>` + `sudo rm -f /var/lib/apt/lists/lock`
   - ⚠️ 谨慎 kill，优先等待

3. **网络受限环境（如中国）拉取 GitHub 主题**
   - 优先选 `apt` 可直接安装的主题（Papirus、Orchis、Bibata）
   - 需要 git clone 的主题改用 ghproxy 镜像
   - 或让用户在浏览器中下载后手动安装

4. **启用 ding@rastersoft.com 后桌面仍无图标**
   - 检查 `show-desktop-icons` 是否为 true
   - 确认扩展在 enabled-extensions 列表中
   - 尝试注销重新登录

5. **Papirus 安装后图标部分未覆盖**
   - 极少数应用图标可能需要额外安装对应软件包
   - Papirus 本身覆盖 6000+ 应用，99% 场景足够

6. **gsettings 写入后不生效**
   - `gsettings` 操作的是用户级 dconf 数据库，即时生效
   - 如果完全不生效，检查是否在错误的 $DISPLAY/$WAYLAND_DISPLAY 下
   - 可以确认 `echo $DBUS_SESSION_BUS_ADDRESS` 是否有效

## 验证检查清单

- [ ] `lsb_release -a` 确认系统版本
- [ ] 图标主题已切换（`gsettings get ... icon-theme`）
- [ ] GTK 主题已切换（`gsettings get ... gtk-theme`）
- [ ] Shell 主题已切换（`gsettings get ... user-theme name`）
- [ ] 鼠标指针已切换（`gsettings get ... cursor-theme`）
- [ ] Desktop Icons NG 已启用并配置
- [ ] Dock 图标大小/位置/透明度符合预期
- [ ] 字体渲染已优化（rgba + slight）
- [ ] 已告知用户重新登录/重启 Shell
- [ ] Emoji 支持已安装（`apt list --installed | grep noto-color-emoji`）
