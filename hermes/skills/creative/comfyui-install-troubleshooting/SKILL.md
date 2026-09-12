---
name: comfyui-install-troubleshooting
description: ComfyUI 安装排障——PYTHONPATH污染、模型下载、桌面图标、端口冲突。
version: 1.0.0
---

# ComfyUI 安装排障（本系统）

## 安装路径

| 项目 | 路径 |
|------|------|
| ComfyUI | `/home/bobobears/comfy/ComfyUI` |
| 虚拟环境 | `/home/bobobears/comfy/ComfyUI/venv` |
| 启动脚本 | `/home/bobobears/comfy/ComfyUI/start.sh` |
| 桌面图标 | `~/Desktop/comfyui.desktop` |
| 端口 | 8189（避免与 HRMS 8188 冲突） |

## 关键问题 1: PYTHONPATH 污染

Hermes agent 的 `PYTHONPATH` 环境变量会将 Hermes venv 的 `site-packages` 注入到所有子进程中，导致 ComfyUI 加载错误的依赖版本（如 `tokenizers 0.23.1` 而非 ComfyUI 需要的 `0.22.2`）。

**修复：** 所有 ComfyUI 相关操作必须在 `PYTHONPATH=""` 环境下执行：

```bash
# 启动
PYTHONPATH="" /home/bobobears/comfy/ComfyUI/venv/bin/python main.py

# pip install
PYTHONPATH="" ./venv/bin/pip install ...

# 创建 venv 时也受影响 — 如果 venv 加载了外部包，需 rm -rf venv && python3 -m venv --clear venv 重建
```

启动脚本 `start.sh` 已内置 `export PYTHONPATH=""`。

## 关键问题 2: 模型下载

### huggingface-cli 已废弃
`huggingface-cli download` 不再工作，必须用 `hf download`。

### HuggingFace 镜像站不支持 Xet 格式
`hf-mirror.com` 上的模型如果使用了 Xet 存储格式（如 Comfy-Org/MiniMax-H3），`hf download` 会报 `401 Unauthorized` 错误。但 `curl` 直接下载 resolve URL 可以绕过 Xet 客户端。

### 大文件下载用 aria2c（推荐）
对于 >5GB 的模型文件，curl 容易在 HTTP/2 stream 中断连。用 aria2c 支持断点续传和多连接：

```bash
aria2c --continue=true \
  --max-connection-per-server=5 \
  --min-split-size=10M \
  --seed-time=0 \
  --check-certificate=false \
  "https://hf-mirror.com/Comfy-Org/MiniMax-H3/resolve/main/diffusion_models/xxx.safetensors" \
  -o xxx.safetensors
```

### 后台 shell 找不到 PATH
后台进程（`terminal(background=true)`）不继承完整 PATH，`hf`、`uv`、`uvx` 等命令找不到。解决方法：
1. 使用绝对路径（如 `/home/bobobears/.hermes/hermes-agent/venv/bin/hf`）
2. 或者创建 bash 脚本，在脚本中设置 `export PATH=...`

## 关键问题 3: GNOME 桌面图标

GNOME 桌面 `.desktop` 文件不支持 `Terminal=true`。需要显式调用终端模拟器：

```ini
[Desktop Entry]
Type=Application
Name=ComfyUI
Exec=/usr/bin/gnome-terminal -- /home/bobobears/comfy/ComfyUI/start.sh
Icon=/home/bobobears/comfy/ComfyUI/comfyui-icon.png
Terminal=false
StartupNotify=false
```

并且需要标记为受信任：
```bash
gio set ~/Desktop/comfyui.desktop metadata::trusted 1
chmod +x ~/Desktop/comfyui.desktop
```

## 关键问题 4: git clone 在后台 shell 中只下载 .git 元数据

`terminal(background=true)` 执行的 `git clone` 可能只下载 `.git` 目录而不 checkout 工作文件。始终使用前台模式：
```bash
# 前台（推荐）
git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git
```

## 模型文件位置

```
/home/bobobears/comfy/ComfyUI/models/
├── diffusion_models/    # MiniMax-H3 扩散模型
├── text_encoders/       # 文本编码器
├── vae/                 # VAE
├── checkpoints/         # 传统 checkpoint 模型
└── ...
```

## 验证安装

```bash
curl -s http://127.0.0.1:8189/system_stats | python3 -m json.tool
```

检查 `devices[0].name` 是否显示 `cuda:0 NVIDIA GB10`。
