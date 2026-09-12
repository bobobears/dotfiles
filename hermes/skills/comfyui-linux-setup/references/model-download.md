# ComfyUI 模型下载

## 方法对比

| 方法 | 可靠性 | 速度 | 备注 |
|------|--------|------|------|
| huggingface-cli | ⭐⭐⭐ | 快 | 支持断点续传，推荐 |
| comfy-cli | ⭐⭐ | 一般 | 需要 comfy-cli 已装 |
| curl | ⭐ | 慢 | 大文件易超时，无断点续传 |

## huggingface-cli（推荐）

```bash
export HF_ENDPOINT=https://hf-mirror.com
huggingface-cli download <repo> <files...> --local-dir ~/comfy/ComfyUI/models
```

文件会自动放到正确的子目录。

## curl（备用）

```bash
curl -L "https://hf-mirror.com/<repo>/resolve/main/<path>" -o <dest>
```

注意：镜像站有时返回错误页面而非真实文件，下载后检查文件大小。

## 常见模型

### MiniMax-H3（视频生成）

```bash
huggingface-cli download Comfy-Org/MiniMax-H3 \
  diffusion_models/minimax_h3_fl2va_pruned_fp8_scaled.safetensors \
  text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors \
  vae/minimax_h3_video_vae_fp16.safetensors \
  --local-dir ~/comfy/ComfyUI/models
```

### Flux Dev（图像生成）

```bash
huggingface-cli download Comfy-Org/flux1-dev-fp8 \
  flux1-dev-fp8.safetensors \
  --local-dir ~/comfy/ComfyUI/models/checkpoints
```

### SDXL

```bash
huggingface-cli download stabilityai/stable-diffusion-xl-base-1.0 \
  sd_xl_base_1.0.safetensors \
  --local-dir ~/comfy/ComfyUI/models/checkpoints
```