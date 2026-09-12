---
name: pillow-video
description: "Generate animated explainer videos with Pillow and edge-tts."
version: 1.0.0
---

# Pillow Video Production

Generate animated explainer videos using Pillow for frame-by-frame rendering, edge-tts for Chinese voiceover, and ffmpeg for synthesis. Lightweight alternative to Manim when you need quick training/科普 videos without LaTeX or mathematical content.

## When to use

- User requests training videos, explainer videos, or concept presentations (non-mathematical)
- Chinese voiceover needed (edge-tts has excellent Mandarin support)
- Quick turnaround needed (no Manim install/compile overhead)
- Content is text-heavy with bullet points rather than geometric/mathematical

## Prerequisites

- `pip install Pillow`
- `pip install edge-tts`
- `ffmpeg` installed
- Chinese fonts: `fc-list :lang=zh -f "%{file}\n" | grep noto`
  - Regular: `/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`
  - Bold: `/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc`

## Pipeline

```
SCRIPT → VOICEOVER → FRAMES → ENCODE → STITCH → FINAL
```

### 1. Write script (scene-by-scene)

Split into scenes. Each scene = one audio clip + one set of frames.

**Critical: edge-tts English abbreviation handling**
- Write `A I` not `AI` — edge-tts reads `AI` as "诶诶" not "A I"
- Write `E x c e l` not `Excel` — same issue
- Write `Siri` as-is (proper noun works)

Each scene 150-300 Chinese characters → 15-40 seconds audio.

### 2. Generate voiceover

```bash
edge-tts --voice zh-CN-YunxiNeural --rate="+2%" \
  --text "文案内容" --write-media scene_01.mp3
```

Voice options:
- `zh-CN-YunxiNeural` — male, energetic
- `zh-CN-XiaoxiaoNeural` — female, warm
- `zh-CN-YunjianNeural` — male, professional
- `zh-CN-XiaoyiNeural` — female, lively

### 3. Get audio duration

```bash
ffprobe -v quiet -show_entries format=duration -of csv=p=0 scene_01.mp3
# Returns: 17.160000
```

### 4. Generate frames (modular architecture)

**CRITICAL: Split into multiple files to avoid 8K token timeout on write_file.**

| File | Purpose |
|------|---------|
| `particles.py` | Particle system (floating dots + connection lines) |
| `renderer.py` | Background gradient + glow effects |
| `scene_render.py` | Per-scene frame rendering (text fly-in, transitions) |
| `main.py` | Orchestration + ffmpeg encoding |

### 5. Encode and stitch

```bash
# Per-scene: frames + audio → MP4
ffmpeg -y -framerate 30 -i frames/%05d.png -i audio.mp3 \
  -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p \
  -c:a aac -b:a 192k -shortest scene.mp4

# Concat all scenes
echo "file 'scene_01.mp4'" > concat.txt
ffmpeg -y -f concat -safe 0 -i concat.txt -c copy final.mp4
```

## Scene rendering patterns

### Background
- Dynamic gradient (deep blue → deep purple) with time-varying shift
- Moving glow orb: `glow_x = w/2 + 200*sin(t*0.01)`
- Particle overlay: 80 particles, connection lines when distance < 150px

### Text animations
- **Fly-in**: `ease_out_cubic`, offset_y = `(1-t)*40` from below
- **Staggered lines**: `line_delay = 0.5 / len(non_empty_lines)`
- **Title glow**: `alpha = 80 * (0.5 + 0.5*sin(frame*0.05))`
- **Decorative line**: width animates from 300 to 700 over first 15% of scene

### Transitions
- Fade in: first 8% of frames
- Fade out: last 8% of frames
- Use `Image.alpha_composite` with black overlay

## Pitfalls

1. **edge-tts abbreviation misread**: `AI` → "诶诶", `Excel` → "埃塞勒". Always space out: `A I`, `E x c e l`
2. **Empty lines list**: Title/ending scenes may have no content lines → `max(len(lines), 1)` in division
3. **Single file timeout**: Scripts >8K tokens timeout on write_file. Always split into modules
4. **TTC font loading**: `ImageFont.truetype()` works with `.ttc` but needs full absolute path
5. **Zero-division on total_frames**: Use `max(total_frames - 1, 1)` in progress calculation
6. **Memory with many frames**: 4691 frames × 1920×1080 RGBA = ~33GB if all held in memory. Save to disk per-scene, don't accumulate

## Color palette

```python
BG_TOP = (15, 23, 42)      # Deep navy
BG_BOTTOM = (30, 27, 75)   # Deep purple
ACCENT = (56, 189, 248)    # Cyan
ACCENT2 = (167, 139, 250)  # Purple
WHITE = (255, 255, 255)
GRAY = (148, 163, 184)
GREEN = (52, 211, 153)
RED = (248, 113, 113)
YELLOW = (251, 191, 36)
```

## Output specs

- Resolution: 1920×1080 (1080p)
- FPS: 30
- Video codec: libx264, CRF 18, yuv420p
- Audio codec: AAC, 192kbps
- Typical output: 7-45MB for 2-5 minute videos
