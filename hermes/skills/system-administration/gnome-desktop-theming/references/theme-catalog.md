# GNOME 桌面主题目录

> 适用于 Ubuntu 24.04 LTS (GNOME 46+)
> 更新于 2026-06-24

## 图标主题

### Papirus — ⭐ 最流行
| 属性 | 值 |
|------|-----|
| **风格** | 扁平现代，6000+ 图标，覆盖极全 |
| **变体** | Papirus / Papirus-Dark / Papirus-Light |
| **安装** | `sudo apt install papirus-icon-theme` |
| **GitHub** | https://github.com/PapirusDevelopmentTeam/papirus-icon-theme |
| **预览** | https://github.com/PapirusDevelopmentTeam/papirus-icon-theme#screenshots |

### Tela Circle — ⭐ 圆角精致
| 属性 | 值 |
|------|-----|
| **风格** | 圆角方形图标，统一性极强，12+ 配色 |
| **变体** | Tela-circle / Tela-circle-dark / Tela-circle-dracula / ... |
| **安装** | `git clone https://github.com/vinceliuice/Tela-circle-icon-theme && cd Tela-circle-icon-theme && ./install.sh` |
| **GitHub** | https://github.com/vinceliuice/Tela-circle-icon-theme |
| **预览** | https://github.com/vinceliuice/Tela-circle-icon-theme#screenshots |

### McMojave Circle — ⭐ macOS 风格
| 属性 | 值 |
|------|-----|
| **风格** | 苹果 Big Sur / Monterey 风格的圆形渐变图标 |
| **安装** | `git clone https://github.com/vinceliuice/McMojave-circle && cd McMojave-circle && ./install.sh` |
| **GitHub** | https://github.com/vinceliuice/McMojave-circle |
| **预览** | https://github.com/vinceliuice/McMojave-circle#screenshots |

### Colloid — ⭐ 新锐热门
| 属性 | 值 |
|------|-----|
| **风格** | 现代柔和，深浅色都好看，多配色 |
| **安装** | `git clone https://github.com/vinceliuice/Colloid-icon-theme && cd Colloid-icon-theme && ./install.sh` |
| **GitHub** | https://github.com/vinceliuice/Colloid-icon-theme |
| **预览** | https://github.com/vinceliuice/Colloid-icon-theme#screenshots |

### Yaru — Ubuntu 官方（预装）
| 属性 | 值 |
|------|-----|
| **风格** | Ubuntu 紫橙配色，已预装 |
| **变体** | Yaru / Yaru-dark / Yaru-*color* (bark, blue, magenta, olive, purple, red, sage, viridian) |
| **切换** | `gsettings set org.gnome.desktop.interface icon-theme "Yaru"` |

## GTK/Shell 主题

### Orchis — ⭐ 推荐（apt 直接安装）
| 属性 | 值 |
|------|-----|
| **风格** | Material Design，配色丰富 |
| **变体** | Orchis / Orchis-Dark / Orchis-Light / Orchis-[Color]-[Variant] |
| **颜色** | Green, Grey, Orange, Pink, Purple, Red, Teal, Yellow |
| **紧凑** | 每种颜色都有 -Compact 变体 |
| **安装** | `sudo apt install orchis-gtk-theme` |
| **GitHub** | https://github.com/vinceliuice/Orchis-theme |
| **切换 GTK** | `gsettings set org.gnome.desktop.interface gtk-theme "Orchis-Dark"` |
| **切换 WM** | `gsettings set org.gnome.desktop.wm.preferences theme "Orchis-Dark"` |
| **切换 Shell** | `gsettings set org.gnome.shell.extensions.user-theme name "Orchis-Dark"` |

### Materia
| 属性 | 值 |
|------|-----|
| **风格** | Material Design，扁平现代 |
| **安装** | `sudo apt install materia-gtk-theme` |
| **切换** | `gsettings set org.gnome.desktop.interface gtk-theme "Materia-dark"` |

## 鼠标指针主题

### Bibata — ⭐ 最流行
| 属性 | 值 |
|------|-----|
| **风格** | 现代圆润，Material Design 风格 |
| **变体** | Bibata-Modern-Classic / Bibata-Modern-Ice / Bibata-Modern-Amber / Bibata-Original-Classic / ... |
| **安装** | `sudo apt install bibata-cursor-theme` |
| **切换** | `gsettings set org.gnome.desktop.interface cursor-theme "Bibata-Modern-Classic"` |
| **大小** | `gsettings set org.gnome.desktop.interface cursor-size 24` |

### phinger — ⭐ 高度可定制
| 属性 | 值 |
|------|-----|
| **风格** | 号称"最过度设计的鼠标指针" |
| **安装** | `sudo apt install phinger-cursor-theme` |
| **GitHub** | https://github.com/phinger-cursor/phinger-cursor |


## Apt 可安装速查

```bash
# 一键安装全部推荐主题
sudo apt install -y \
  papirus-icon-theme \
  orchis-gtk-theme \
  bibata-cursor-theme \
  fonts-noto-color-emoji

# 其他可选
sudo apt install -y materia-gtk-theme phinger-cursor-theme
```
