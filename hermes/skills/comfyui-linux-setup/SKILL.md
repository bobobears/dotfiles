---
name: comfyui-linux-setup
description: "ComfyUI on Linux: install, env isolation, desktop, models."
version: 1.0.0
---

# ComfyUI Linux 安装与配置

## 安装路径

默认 `~/comfy/ComfyUI`。

## 关键坑

### GB10/新 GPU 检测失败

`scripts/hardware_check.py` 不认识新 GPU，返回 `verdict: cloud`。用 `nvidia-smi` 确认后直接安装。

### PYTHONPATH 污染

Hermes agent 的 `PYTHONPATH` 会污染 ComfyUI venv（tokenizers 版本冲突）。启动必须：

```bash
PYTHONPATH="" ./venv/bin/python main.py --port 8189
```

验证：`./venv/bin/python -c "import sys; print([p for p in sys.path if 'site-packages' in p])"` 不应出现 hermes-agent 路径。

### GNOME 桌面图标

不支持 `Terminal=true`。正确写法见 `references/desktop-icon.md`。

### 端口冲突

ComfyUI 默认 8188，HRMS 也用 8188。改为 8189。

## 模型下载

用 huggingface-cli（比 curl 可靠）：

```bash
export HF_ENDPOINT=https://hf-mirror.com
huggingface-cli download Comfy-Org/MiniMax-H3 \
  diffusion_models/xxx.safetensors \
  --local-dir ~/comfy/ComfyUI/models
```

## 启动/停止

```bash
# 启动
cd ~/comfy/ComfyUI && PYTHONPATH="" nohup ./venv/bin/python main.py --port 8189 > /tmp/comfyui.log 2>&1 &

# 停止
pkill -f "main.py.*8189"
```