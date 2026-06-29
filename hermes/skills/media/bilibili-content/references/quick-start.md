# Bilibili Content — Quick Start

## One-shot transcript from Bilibili URL

```bash
source ~/whisper-env/bin/activate
BBDown "BV_ID" --audio-only --work-dir /path/to/output
whisper /path/to/output/*.m4a --model tiny --language zh --output_dir /path/to/output
cat /path/to/output/*.txt
```

## BBDown install (ARM64, China network)

```bash
aria2c -x 8 -s 8 -k 1M \
  "https://github.com/nilaoda/BBDown/releases/download/1.6.3/BBDown_1.6.3_20240814_linux-arm64.zip" \
  -o BBDown.zip
unzip BBDown.zip
chmod +x BBDown
mkdir -p ~/.local/bin
cp BBDown ~/.local/bin/
```

## Whisper install

```bash
python3 -m venv ~/whisper-env
source ~/whisper-env/bin/activate
pip install openai-whisper
```

## Example session commands

```bash
# Download audio only (fast, ~6MB for 6min video)
BBDown "https://www.bilibili.com/video/BV1afoaBHE1M/" --audio-only --work-dir "/home/bobobears/视频"

# Transcribe (6min video → ~60s with tiny model on GPU)
whisper "如何5分钟部署自动化Github3万star 股票分析工具.m4a" \
  --model tiny --language zh --output_format txt --output_dir .
```
