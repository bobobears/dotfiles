# MiniMax-H3 文生视频工作流（ComfyUI API）

## 前置条件

- ComfyUI 0.31.0+ 已安装并运行在 `http://127.0.0.1:8189`
- 模型已下载：
  - `models/diffusion_models/minimax_h3_fl2va_pruned_fp8_scaled.safetensors` (20GB)
  - `models/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` (15GB)
  - `models/vae/minimax_h3_video_vae_fp16.safetensors` (4.9GB)

## 原生节点（无需自定义节点）

MiniMax-H3 在 ComfyUI 0.31.0 中**原生集成**，无需安装额外自定义节点。可用节点：

| 节点 | 用途 |
|------|------|
| `UNETLoader` | 加载扩散模型（`weight_dtype: fp8_e4m3fn`） |
| `CLIPLoader` | 加载文本编码器（`type: minimax`） |
| `VAELoader` | 加载 VAE |
| `MiniMaxH3SigmaShift` | 设置 shift 参数（video: 12.0, audio: 3.0） |
| `CLIPTextEncode` | 编码正/负提示词 |
| `EmptyMiniMaxH3LatentAV` | 创建视频潜空间（宽/高/帧数） |
| `KSampler` | 采样生成 |
| `VAEDecode` | 解码潜空间为图像帧 |
| `SaveWEBM` | 保存为 WebM 视频 |

## 帧数与时长

`EmptyMiniMaxH3LatentAV.length` 步进为 17（17k+5 网格）：
- `51` 帧 ≈ 2 秒（适合测试）
- `85` 帧 ≈ 3.5 秒
- `124` 帧 ≈ 5 秒（推荐）
- `161` 帧 ≈ 6.7 秒
- `362` 帧 ≈ 15 秒（训练范围上限）

分辨率建议 672×376（测试）或 848×480（标准）。

## API 提交工作流

```bash
# 工作流 JSON 保存为 workflow.json，然后用：
curl -s -X POST http://127.0.0.1:8189/prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": <workflow_json>}'

# 返回 prompt_id，用于查询进度：
curl -s http://127.0.0.1:8189/history/<prompt_id>

# 查询队列：
curl -s http://127.0.0.1:8189/queue
```

## 完整工作流模板（文生视频）

```json
{
  "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "minimax_h3_fl2va_pruned_fp8_scaled.safetensors", "weight_dtype": "fp8_e4m3fn"}},
  "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "type": "minimax"}},
  "3": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_video_vae_fp16.safetensors"}},
  "4": {"class_type": "MiniMaxH3SigmaShift", "inputs": {"model": ["1",0], "shift_video": 12.0, "shift_audio": 3.0}},
  "5": {"class_type": "CLIPTextEncode", "inputs": {"text": "YOUR_PROMPT_HERE", "clip": ["2",0]}},
  "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry, low quality, distorted, watermark, text, ugly, deformed", "clip": ["2",0]}},
  "7": {"class_type": "EmptyMiniMaxH3LatentAV", "inputs": {"width": 848, "height": 480, "length": 124}},
  "8": {"class_type": "KSampler", "inputs": {"model": ["4",0], "seed": 42, "steps": 20, "cfg": 7.0, "sampler_name": "euler", "scheduler": "normal", "positive": ["5",0], "negative": ["6",0], "latent_image": ["7",0], "denoise": 1.0}},
  "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8",0], "vae": ["3",0]}},
  "10": {"class_type": "SaveWEBM", "inputs": {"images": ["9",0], "filename_prefix": "output", "codec": "vp9", "fps": 24.0, "crf": 28.0}}
}
```

## 性能参考

- 672×376, 51 帧, 20 steps: ~2.5 分钟（GB10）
- 848×480, 124 帧, 20 steps: ~6-8 分钟（预估）

## 提示词风格

MiniMax-H3 对英文提示词响应更好。描述应包含：
- 主体（what）
- 动作/变化（how it moves）
- 风格/色调（style, lighting, color）
- 镜头运动（camera movement）
