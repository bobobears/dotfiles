---
name: bilibili-content
description: "Download Bilibili videos & transcribe with Whisper (speech-to-text) on Linux, incl. ARM64 & China-network workarounds."
tags: [bilibili, bbdown, whisper, stt, chinese, video, aarch64]
platforms: [linux, macos, windows]
---

# Bilibili Content Tool

## When to use

Use when the user:
- Shares a Bilibili URL and wants a transcript, summary, or text-based understanding of the video
- Asks to download Bilibili video/audio locally
- Wants to set up BBDown or Whisper for video content extraction
- Asks about understanding video/audio content from Chinese platforms

## Architecture

Unlike YouTube, Bilibili does not expose public transcripts/subtitles via API. The workflow is:

```
Bilibili URL → BBDown (audio-only) → audio file → Whisper (STT) → text → content processing
```

BBDown and Whisper must be installed first (one-time setup).

## Setup

### 1. Install BBDown (Bilibili Downloader)

**Latest version**: check https://github.com/nilaoda/BBDown/releases

```bash
# Determine architecture
uname -m
# → x86_64 or aarch64
```

**For China / slow-network environments (must use aria2c for multi-threaded download)**:

```bash
cd /tmp
aria2c -x 8 -s 8 -k 1M \
  "https://github.com/nilaoda/BBDown/releases/download/1.6.3/BBDown_1.6.3_20240814_linux-ARCH.zip" \
  -o BBDown.zip
unzip BBDown.zip
chmod +x BBDown
mkdir -p ~/.local/bin
cp BBDown ~/.local/bin/
# verify
BBDown --help
```

Replace `ARCH` with `arm64` (aarch64) or `x64` (x86_64).

### 2. Install Whisper (OpenAI Speech-to-Text)

```bash
cd ~ && python3 -m venv whisper-env
source ~/whisper-env/bin/activate
pip install openai-whisper
```

On ARM64+NVIDIA systems, the CUDA-enabled PyTorch wheel is installed automatically. Verify:

```bash
source ~/whisper-env/bin/activate
python3 -c "import whisper; m = whisper.load_model('tiny', device='cuda'); print('OK')"
```

First run auto-downloads the model (~72MB for `tiny`). Subsequent runs use the cached model in `~/.cache/whisper/`.

### Model Reference

| Model   | Size    | Speed  | Accuracy | Use Case                   |
|---------|---------|--------|----------|----------------------------|
| tiny    | 72 MB   | ⚡fast | adequate | Quick drafts, testing      |
| base    | 139 MB  | ⚡fast | fair     | Casual transcription       |
| small   | 461 MB  | 🏃     | good     | Default for most tasks     |
| medium  | 1.4 GB  | 🚶slow | very good| Higher accuracy needs      |
| large-v3| 2.9 GB  | 🐢slow | best     | Production-grade output    |

## Workflow

### Quick one-shot: download + transcribe

```bash
# 1. Activate Whisper environment
source ~/whisper-env/bin/activate

# 2. Download audio only (fastest)
BBDown "BV1afoaBHE1M" --audio-only

# 3. Transcribe with Whisper
whisper "video_title.m4a" --model tiny --language zh

# 4. Output formats (txt, srt, vtt, tsv, json, all)
whisper "video_title.m4a" --model tiny --language zh --output_format all
```

### Step by step

```bash
# Download
BBDown "BVxxxx" --audio-only

# Transcribe (Chinese video)
whisper "output.m4a" --model small --language zh --output_dir .

# Read the text output
cat output.txt
```

### Common BBDown options

```bash
# Download with specific quality
BBDown "BVxxxx" -q "8K 超高清, 1080P 高码率, 1080P 高清"

# Download multi-P videos
BBDown "BVxxxx" -p 1,3,5     # specific parts
BBDown "BVxxxx" -p all        # all parts

# List available streams without downloading
BBDown "BVxxxx" -info

# Download with aria2c for speed
BBDown "BVxxxx" --use-aria2c

# Download only audio/danmaku/subtitles
BBDown "BVxxxx" --audio-only
BBDown "BVxxxx" --danmaku-only
BBDown "BVxxxx" --sub-only

# API mode for restricted videos
BBDown "BVxxxx" --use-tv-api
BBDown "BVxxxx" --use-app-api

# Specify output directory
BBDown "BVxxxx" --work-dir "/path/to/output"
```

### Whisper options

```bash
# Basic usage
whisper input.mp3 --model tiny --language zh

# With timestamps (default)
whisper input.mp3 --model small --language zh --output_format srt

# Plain text only (no timestamps)
whisper input.mp3 --model tiny --language zh --output_format txt

# Translate to English (for Chinese videos)
whisper input.mp3 --model small --task translate
```

## Pitfalls

- **Slow GitHub from China**: Single-threaded `wget`/`curl` to GitHub is ~30KB/s. Always use `aria2c -x 8` for multi-threaded downloads or GitHub archive zips.
- **raw.githubusercontent.com DNS pollution in China**: resolves to 0.0.0.0. Use `ghproxy.net/https://raw.githubusercontent.com/...` prefix or GitHub API instead.
- **GitHub API rate limit**: 60 req/hour for unauthenticated. For bulk file downloads, use zipball API endpoint (`api.github.com/repos/.../zipball/main`) with aria2c, or authenticate with a token.
- **BBDown login**: Without Bilibili account login, high-quality streams (1080p+) may be restricted. Use `--use-tv-api` or `--use-app-api` as workaround.
- **Whisper model SHA mismatch on retry**: If the initial download was interrupted, Whisper may re-download the full model. Delete `~/.cache/whisper/*.pt` and retry.
- **Whisper + pip conflict**: Install Whisper in its own venv (not the Hermes venv) to avoid dependency conflicts with Hermes agent packages.
- **CUDA on ARM64**: If CUDA is available but Whisper warns "Performing inference on CPU when CUDA is available", pass `device='cuda'` explicitly or set `device=cuda` via the CLI.
