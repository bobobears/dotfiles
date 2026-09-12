---
name: scripted-video
description: Use when making a video from a script with TTS voiceover.
---

# Scripted Video Generation

从脚本生成带配音的短视频（科普、培训、演示等场景）。

## 触发条件

- 用户要求"做个视频"、"把大纲做成视频"、"配音视频"
- 需要将文字内容转化为带画面的视频
- 需要中文 TTS 配音

## 工具链

| 工具 | 用途 | 安装 |
|------|------|------|
| `edge-tts` | 中文 TTS 配音（免费，自然度高） | `pip3 install edge-tts` |
| `Pillow` | 生成每一帧画面 | `pip3 install Pillow` |
| `ffmpeg` | 帧序列 + 音频合成视频 | 系统预装 |

## 工作流程

### 1. 写逐字稿（按场景分段）

将内容拆成场景，每个场景一个段落。每段约 100-300 字（15-40 秒）。

**注意**：
- AI 播报时，"AI"要写成 "A I"（加空格），否则语音识别为"爱你"
- Excel 写成 "E x c e l"，同理
- 总字数约 1000-1200 字对应 2-3 分钟视频

### 2. 生成配音（edge-tts）

```bash
edge-tts --voice zh-CN-YunxiNeural --rate="+2%" --text "文案" --write-media output.mp3
```

**常用中文音色**：

| 音色 | 性别 | 风格 | 适用场景 |
|------|------|------|---------|
| `zh-CN-YunxiNeural` | 男 | 年轻有活力 | 科普、培训 |
| `zh-CN-XiaoxiaoNeural` | 女 | 温暖亲切 | 教育、讲解 |
| `zh-CN-YunjianNeural` | 男 | 沉稳专业 | 正式报告 |
| `zh-CN-XiaoyiNeural` | 女 | 活泼 | 轻松内容 |

**参数**：
- `--rate`：语速，`"+2%"` 微快，`"-5%"` 放慢
- 批量生成时写脚本逐个调用（edge-tts 不支持并发）

### 3. 获取每段音频时长

```bash
ffprobe -v quiet -show_entries format=duration -of csv=p=0 scene.mp3
```

用于计算帧数：`总帧数 = int(时长 × FPS)`，FPS 通常为 30。

### 4. 生成画面帧（Pillow）

用 Pillow 逐帧绘制：
- 深色渐变背景（深蓝→深紫）
- 标题 + 内容文字逐行出现（缓入动画）
- 装饰性圆形/几何图形
- 每段结尾淡出

**中文字体路径**：
```python
FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_BOLD_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
```

**帧保存**：`frames/scene_01/00000.png`, `00001.png`, ...

### 5. 合成视频（ffmpeg）

每个场景：帧序列 + 音频 → 视频片段

```bash
ffmpeg -y -framerate 30 \
  -i frames/scene_01/%05d.png \
  -i audio/scene_01.mp3 \
  -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p \
  -c:a aac -b:a 192k \
  -shortest \
  scene_01.mp4
```

合并所有场景：

```bash
# concat_list.txt:
# file 'scene_01.mp4'
# file 'scene_02.mp4'
# ...

ffmpeg -y -f concat -safe 0 -i concat_list.txt -c copy final.mp4
```

## 输出规格

- 分辨率：1920×1080 (1080p)
- 帧率：30 FPS
- 视频编码：H.264 (libx264, CRF 18)
- 音频编码：AAC 192kbps
- 像素格式：yuv420p（兼容播放器）

## 注意事项

- **帧数计算**：`int(duration * 30)`，不要四舍五入
- **淡入淡出**：每段开头 10% 淡入，结尾 10% 淡出，避免场景切换生硬
- **文字出现节奏**：内容行每隔 0.08-0.15 的进度出现一行，配合配音节奏
- **临时文件清理**：帧 PNG 文件占用大（约 1-2 MB/帧），合成后立即删除
- **中文字体**：用 `fc-list :lang=zh -f "%{file}\n"` 查找可用字体

## 参考文件

- `references/scene_templates.md` — 场景类型模板（标题/内容/结尾/警告）
