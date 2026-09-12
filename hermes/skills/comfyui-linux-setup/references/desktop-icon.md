# GNOME 桌面图标正确写法

## 问题

GNOME 桌面不支持 `.desktop` 文件中的 `Terminal=true`。设置它会导致双击无反应或报错"无法执行默认终端模拟器"。

## 正确写法

创建 `~/Desktop/comfyui.desktop`：

```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=ComfyUI
Exec=/usr/bin/gnome-terminal -- /path/to/start.sh
Icon=/path/to/icon.png
Terminal=false
Categories=Graphics;Art;
StartupNotify=false
```

关键：
- `Terminal=false`（不是 true）
- `Exec` 显式调用 `gnome-terminal --` 来打开终端窗口
- 启动脚本（start.sh）内部处理 `PYTHONPATH=""` 等环境变量

## 标记为受信任

```bash
gio set ~/Desktop/comfyui.desktop metadata::trusted 1
chmod +x ~/Desktop/comfyui.desktop
```

## 启动脚本（start.sh）

```bash
#!/bin/bash
export PYTHONPATH=""
exec /path/to/ComfyUI/venv/bin/python /path/to/ComfyUI/main.py --listen 0.0.0.0 --port 8189 "$@"
```

## 图标

ComfyUI 自带图标在 venv 内部，路径不稳定。复制到项目根目录：

```
/path/to/ComfyUI/comfyui-icon.png
```

来源：`venv/lib/python3.x/site-packages/comfyui_frontend_package/static/assets/images/comfy-icon-512.png`