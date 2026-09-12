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

### ⚠️ Cron Job Resilience — API Fallback

Hermes cron 任务的 LLM 调用可能因 API 短暂不可用而失败（最常见：DeepSeek `[Errno 32] Broken pipe`）。Hermes **没有**内置 `fallback_providers` 配置项——`hermes config set fallback_providers [...]` 写入 yaml 但不会被使用。

**解决方案：在 cron prompt 中加入三级 fallback 指令**

#### 三级降级策略（从 prompt 层面实现）

任务 prompt 中加入以下逻辑段：

```markdown
## 🛡️ Fallback 流程

如果在 LLM 分析阶段遇到 API 调用失败（Broken pipe/timeout/5xx）：

### Fallback A — 尝试本地模型
通过 curl 调用本地 LM Studio API (http://127.0.0.1:1234/v1/chat/completions)

### Fallback B — 纯脚本基础报告（无 LLM）
执行数据获取并生成纯技术指标报告（SQLite 查询最新行情数据，计算 MA/涨跌幅）

### Fallback C — 推送错误通知
如果以上途径都失败，推送飞书消息通知用户手动运行
```

**关键配置（确保 fallback 能执行）**：
- ❌ **不要**在 cron 任务上锁定 `model`/`provider` — 锁定后 agent 的"大脑"就是那个 provider，API 挂了 agent 连思考都无法进行，prompt 里的 fallback 逻辑根本不会执行
- ✅ **让 cron 任务使用默认模型链**（不设置 model/provider）— 这样 DeepSeek 不可用时会自动回退到本地 LM Studio 模型，agent 仍然能思考并执行 fallback 逻辑
- ✅ DSA 系统本身的 LLM 分析（`main.py` 内部调用的 SiliconFlow/DeepSeek）是独立的，与 Hermes agent 的模型链无关

#### ⚠️ Broken pipe 故障诊断

如果 cron 任务报 `[Errno 32] Broken pipe`：
1. 查看日志：`grep 'Broken pipe' ~/.hermes/logs/errors.log`
2. 确认是哪个 API 挂了（日志里有 `provider=` 和 `base_url=`）
3. 如果 agent 的 model/provider 被硬编码到挂了的那个 provider，清除硬编码：编辑 `~/.hermes/cron/jobs.json`，将对应任务的 `model` 和 `provider` 改为 `null`
4. 下次运行 agent 会使用默认模型链（config.yaml 中的 `model.default` + `model.provider`），DeepSeek 恢复后 DSA 脚本内部仍会走自己的 LLM 通道

#### ⚠️ 推送语言要求

该 cron 任务运行后自动投递到飞书。**推送内容必须使用中文。** 在 prompt 末尾显式添加语言指令：

```markdown
报告将在你的最终回复中自动投递到飞书。**所有输出必须使用中文。**
```

#### Known Pitfall
- ❌ `hermes config set fallback_providers` — 该字段不存在于 Hermes schema。即使写入 config.yaml 也不会被消费。不要尝试。
- ❌ 在 cron 任务上锁定 `model`/`provider` 到外部 API（如 DeepSeek）— 当该 API 不可用时，agent 本身无法运行，prompt 里的 fallback 逻辑永远不会执行。这是 `[Errno 32] Broken pipe` 失败的根因。
- ✅ 正确的做法：在 cron prompt 中编写显式 fallback 逻辑（如上所述），同时让 cron 任务使用默认模型链（model/provider 为 null）

### ⚠️ 手动 `run` 会吞掉第二天的计划执行（occurrence 冲突）

`hermes cron run <job>` / `cronjob_manage action=run` 走的是 `claim_job_for_fire()`（**不传 force**），
它会把任务的**下一个计划 occurrence** 当作本次运行的 occurrence 写进 `executions.scheduled_instant`，
并同步推进 `next_run_at`。后果：

> **对每日任务手动补跑一次，第二天同一时刻的计划执行会被判定为「该 occurrence 已完成」而静默跳过。**

这不是猜测——`tools/cronjob_tools.py:_execute_job_now()` 注释原话："a claimed direct run advances next_run_at"。

**症状**：某天 09:00 完全没有任何 scheduled 运行记录（无 output 文件、无推送），
只在**前一天**有一条 `source='direct'` 的运行记录，而它的 `scheduled_instant` 正好等于缺失的那天。

**诊断**：
```bash
sqlite3 -line ~/.hermes/cron/executions.db \
  "SELECT id, source, status, claimed_at, scheduled_instant FROM executions \
   WHERE job_id='<job_id>' ORDER BY rowid DESC LIMIT 5;"
```
只要有一条 `source='direct'` 的记录 `scheduled_instant` 指向将来（同一天上午 09:00 CST = `T01:00:00+00:00`），
那天的计划执行就已经被吞掉。

**修复**（清空被误标的 occurrence，让那天恢复正常触发）：
```bash
sqlite3 ~/.hermes/cron/executions.db \
  "UPDATE executions SET scheduled_instant=NULL WHERE id='<那条 direct 执行的 id>';"
# 校验：应返回 0
sqlite3 ~/.hermes/cron/executions.db \
  "SELECT count(*) FROM executions WHERE job_id='<job_id>' \
   AND scheduled_instant='<被吞掉的 UTC 时间>' AND status='completed';"
```
`next_run_at` 不用动，下一次计划触发会正常执行。

**规避**：故障当天不要急着手动补跑；若已补跑，**必须**检查并清理被吞掉的 occurrence，否则问题会一天天滚下去。

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

## Search & News Configuration

DSA uses SearXNG for stock news/intelligence search. By default it tries to auto-discover public instances from `searx.space` — which **fails in China** (DNS resolution error).

**Fix**: Add to `.env`:
```bash
SEARXNG_BASE_URLS=http://127.0.0.1:8080
SEARXNG_PUBLIC_INSTANCES_ENABLED=false
```

If you have a local SearXNG Docker container running (default port 8080), verify it first:
```bash
docker ps --filter "name=searxng" --format "{{.Names}}\t{{.Status}}"
curl -s "http://127.0.0.1:8080/search?q=test&format=json" | python3 -m json.tool | head -5
```

⚠️ **Common mistake**: The SearXNG Docker container maps to port **8080**, not 8888. Double-check with `docker ps` before configuring.

## Troubleshooting

- **[Errno 32] Broken pipe** — Hermes agent 调用的外部 API（DeepSeek 等）不可用。根因通常是 cron 任务的 `model`/`provider` 被硬编码到该 API。修复：将 jobs.json 中该任务的 `model` 和 `provider` 改为 `null`，让 agent 使用默认模型链（本地 LM Studio）。DSA 脚本内部的 LLM 通道不受影响。
- **Null bytes in .py files**: Re-download via ghproxy raw URL
- **"404 Not Found" __init__.py**: Create empty file
- **Tushare rate limit**: Free tier limits 1 call/min for some endpoints, 1/hr for trade_cal
- **Model not found**: Verify model name with `LLM_SILICONFLOW_MODELS`
- **No push notification**: Check `FEISHU_WEBHOOK_URL` is set and uncommented in .env
- **Stock code not recognized**: Ensure 6-digit code, prefix `sz`/`sh` auto-detected
- **Search fails — "未获取到可用的公共 SearXNG 实例"**: DSA's `.env` is missing `SEARXNG_BASE_URLS`. See [Search & News Configuration](#search--news-configuration) above.
- **筹码分布获取失败 — NameResolutionError**: 东方财富 `push2his.eastmoney.com` DNS 不可达时，筹码分布分析自动跳过，不影响核心评分
- **SearXNG 容器无法启动**:
  - Docker 在 ARM64 (GB10) 上首次拉取镜像较慢（~150MB），需要耐心等待
  - 容器启动后 wikidata 引擎可能超时（国内访问 wikidata.org 慢），但这不影响核心搜索功能
  - 容器管理命令: `cd ~/searxng && docker compose up -d` / `docker compose ps -a`
  - `docker ps --filter "name=searchng"` 过滤可能不匹配（容器名是 `searxng` 不是 `searchng`），用 `docker compose ps -a` 更可靠
