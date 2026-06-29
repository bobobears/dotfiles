---
name: stock-analysis-automation
description: >-
  Deploy, configure, and operate the Daily Stock Analysis (DSA) system —
  an LLM-powered A-share/HK/US stock analysis tool with AI reports,
  Feishu/DingTalk/Telegram push, and scheduled daily runs.
  Covers: China-network deployment, API configuration, and daily ops.
---

# Stock Analysis Automation (DSA 系统)

Deploy and operate the [daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis) project (49k+ ⭐) for automated AI-powered stock analysis with push notifications.

## Quick Deploy

### 1. Get the Source Code

**From China (slow GitHub):**
```bash
# Use aria2c for multi-threaded download
aria2c -x 4 -s 4 "https://github.com/ZhuLinsen/daily_stock_analysis/archive/refs/heads/main.zip"

# Individual files via ghproxy (when raw.githubusercontent.com is DNS-polluted)
curl -sL "https://ghproxy.net/https://raw.githubusercontent.com/ZhuLinsen/daily_stock_analysis/main/{path}" -o "{path}"

# Truncated ZIP recovery — scan for PK\x03\x04 headers and extract manually
```

### 2. Virtual Environment & Dependencies
```bash
cd ~/dsa
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt  # ~150 packages
```

### 3. Configure .env

```bash
# AI Model — SiliconFlow (国内直连, OpenAI-compatible)
LLM_CHANNELS=siliconflow
LLM_SILICONFLOW_PROTOCOL=openai
LLM_SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
LLM_SILICONFLOW_API_KEY=sk-xxx
LLM_SILICONFLOW_MODELS=deepseek-ai/DeepSeek-V3
LLM_SILICONFLOW_ENABLED=true
OPENAI_API_KEY=sk-xxx  # fallback
OPENAI_BASE_URL=https://api.siliconflow.cn/v1

# Stock Watchlist (comma-separated, 沪深 codes)
STOCK_LIST=600519,300750,002594

# Financial Data
TUSHARE_TOKEN=xxx  # Free tier from https://tushare.pro

# Push Notification (pick one)
# FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
# WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx

# General
REPORT_LANGUAGE=zh
DATABASE_URL=sqlite:///data/dsa.db
GENERATION_BACKEND=litellm
```

### 4. Run Analysis
```bash
cd ~/dsa && source venv/bin/activate
python main.py
```

### 5. Start Web UI
```bash
python server.py
# Visit http://localhost:8000
```

## Scheduling Daily Analysis

### Via Hermes Cron (recommended)
```bash
# Daily at 9:00 AM
hermes cron create --schedule "0 9 * * *" \
  --prompt "cd ~/dsa && source venv/bin/activate && python main.py" \
  --name "daily-stock-analysis"
```

## API Keys Reference

| Service | Chinese-Friendly | Free Tier | Get It |
|---------|:----------------:|:---------:|--------|
| SiliconFlow | ✅ 国内直连 | 16元券 | https://cloud.siliconflow.cn |
| Tushare Pro | ✅ 国内 | Basic free | https://tushare.pro |
| DeepSeek | ✅ | 500万tokens | https://platform.deepseek.com |
| Tavily | ❌ | 1000次/月 | https://tavily.com |
| Feishu | ✅ | Free | 群设置→机器人→自定义 |
| 企业微信 | ✅ | Free | 群机器人 Webhook |

## China Network Workarounds

| Problem | Solution |
|---------|----------|
| GitHub download ~30KB/s | Use `aria2c -x 4 -s 4` for multi-thread |
| raw.githubusercontent.com DNS → 0.0.0.0 | Prefix with `https://ghproxy.net/` |
| GitHub API rate limit (60/hr) | Wait 1hr or use ghproxy for file downloads |
| Docker Hub timeout | Try `docker pull` via `dockerpull.com` mirror |
| PyPI slow | Use `-i https://pypi.tuna.tsinghua.edu.cn/simple` |
| Truncated ZIP from GitHub | Extract via PK header scanning (see references/truncated-zip.md) |

## Troubleshooting

- **Null bytes in .py files**: Re-download via ghproxy raw URL
- **"404 Not Found" __init__.py**: Create empty file
- **Tushare rate limit**: Free tier limits 1 call/min for some endpoints, 1/hr for trade_cal
- **Model not found**: Verify model name with `LLM_SILICONFLOW_MODELS`
- **No push notification**: Check `FEISHU_WEBHOOK_URL` is set and uncommented in .env
- **Stock code not recognized**: Ensure 6-digit code, prefix `sz`/`sh` auto-detected
