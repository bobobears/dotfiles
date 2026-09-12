---
name: hermes-web-search-backend
description: Use when Hermes web_search or web_extract fails.
---

# Hermes Web 搜索/提取后端配置与排障

## 何时用

- `web_search` 报 `BRAVE_SEARCH_API_KEY is not set` / `keyless rescue failed`
- `web_extract` 报 `... is a search-only backend and cannot extract URL content`
- 搜索返回 0 条、静默超时
- 需要在国内网络环境下换一个可达的后端

## 核心事实：国内网络下的后端可达性（2026-09 实测，安徽电信）

| 后端 | 需 key | 搜索 | 提取 | 国内可达 |
|------|:------:|:---:|:---:|:---:|
| **firecrawl** | 否（keyless） | ✔ | ✔ | ✅ `api.firecrawl.dev` 200 |
| **tavily** | 否（keyless） | ✔ | ✔ | ✅ `api.tavily.com` 200 |
| exa | 否（keyless） | ✔ | ✔ | ⚠️ `api.exa.ai` 可达，但 keyless MCP 常报 `Unrecognized MCP response shape` |
| parallel | 否（keyless） | ✔ | ✔ | ✅ `search.parallel.ai` |
| keenable | 否（keyless） | ✔ | ✔ | ✅ `api.keenable.ai` |
| brave-free | **是** | ✔ | ✗ | ❌ `api.search.brave.com` 超时 |
| ddgs | 否 | ✔ | ✗ | ❌ `duckduckgo.com` 超时 |
| searxng | 否 | ✔ | ✗ | ❌ 公共实例（searx.be 等）超时 |
| xai | 是 | ✔ | ✗ | ❌ `api.x.ai` 超时 |

**结论（当前生产配置）**：

| 层 | 后端 | 说明 |
|---|---|---|
| 主 | **tavily**（keyed） | `TAVILY_API_KEY` 写 `~/.hermes/.env`；搜索 2.3s、extract 返回干净 markdown 全文（**非片段**，文档标注偏保守），中文命中率好 |
| 兜底 | **firecrawl**（keyless） | 主后端限流时由 keyless 轮询环自动接管，无需额外配置 |

**无 key 时的裸配置**：直接 `hermes config set web.backend firecrawl` —— keyless 双能力，中文正常。

实测数据（2026-09，安徽电信）：

- Tavily search「中国高血压防治指南 2024 降压目标」→ 3 条，首条即期刊 PDF 原文，2.34s
- Tavily extract Cloudflare 文档 → 3,555 字符干净 markdown，2.03s
- Tavily extract 企业微信文档 → **61,777 字符**（超长内容自动落盘 `~/.hermes/cache/web/<host>-<hash>.md`，用 `read_file` 翻页读）

## 排障步骤

### 1. 确认当前后端

```bash
hermes config get web.backend
cd ~/.hermes/hermes-agent && venv/bin/python - <<'PY'
import sys; sys.path.insert(0, ".")
import tools.web_tools as wt
print(wt._get_backend(), wt._get_search_backend(), wt._get_extract_backend())
PY
```

### 2. 测候选后端可达性（6 秒超时足够区分「慢」与「不通」）

```bash
for u in https://api.firecrawl.dev https://api.tavily.com https://api.search.brave.com https://duckduckgo.com; do
  printf "%-34s " "$u"; curl -s -o /dev/null -w "HTTP %{http_code}  %{time_total}s\n" --max-time 6 "$u"
done
```

注意：`HTTP 000` = 超时/不可达；`404` 也算**可达**（只是根路径没有内容）。

### 3. 改后端

```bash
cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak.web_$(date +%Y%m%d_%H%M%S)   # 先备份
hermes config set web.backend firecrawl
hermes config get web.backend                                                    # 回读确认
```

### 4. 验证真实调用

```bash
cd ~/.hermes/hermes-agent && venv/bin/python - <<'PY'
import sys, json, asyncio; sys.path.insert(0, ".")
import tools.web_tools as wt
d = json.loads(wt.web_search_tool("关键词", limit=3))
print(d["success"], len(d["data"]["web"]))     # 字段是 data.web！
r = asyncio.run(wt.web_extract_tool(["https://example.com"], char_limit=800))
print(r[:200])
PY
```

## 陷阱

- **改配置只能走 `hermes config set`**：`patch` / `write_file` 写 `~/.hermes/config.yaml` 会被拒（`Refusing to write to Hermes config file`）。
- **改完无需重启网关**：`load_config()` 按**文件签名**缓存，编辑后自动失效，网关进程同样即时生效。
- **改 `~/.hermes/.env` 才需要重启**：env 层有独立缓存 `_env_cache`，写入后须 `invalidate_env_cache()` 或重启进程。
- **`web_search` 结果字段是 `data.web`**，不是 `data.results`。用错字段会误判成「成功但 0 条结果」。
- **`web.backend` 一旦写入就固定**：之后往 `.env` 补 key **不会**自动改路由，必须显式 `hermes config set`。
- **keyless 轮询环** = `exa → parallel → firecrawl → keenable`，只对「限流型」错误故障转移；非限流错误直接停。
- **`web.provider_tier.<name>: free|paid`** 可强制某家走 keyless（`free`）或 keyed（`paid`，无 key 则报错而非静默降级）。
- **别在 Brave 上浪费时间**：即使配了 `BRAVE_SEARCH_API_KEY`，国内仍超时。
- **`ddgs` 在国内无用**：装得上，但 DuckDuckGo 不通。
- **用浏览器兜底要确认有 Chrome**：`browser_exec` 依赖 Chrome/Chromium；本机只有 firefox，会直接报找不到浏览器。
- **接 keyed 后端要改两处，缺一不可**：① key 追加进 `~/.hermes/.env`（先 `cp -a .env .env.bak.<name>_$(date +%Y%m%d_%H%M%S)`，再 `printf '\nTAVILY_API_KEY=xxx\n' >> .env`）；② `hermes config set web.backend tavily`。**只写 key 不改 backend，路由不会变**。
- **`.env` 是否需重启**：走 `load_env_file` 的路径按文件签名缓存，改完即时生效（实测当前会话立刻可用）；若发现读不到，`hermes` 进程重启一次即可。
- **验证 keyed 后端是否真的生效**：`venv/bin/python -c "import sys;sys.path.insert(0,'.');import tools.web_tools as wt;print(wt._get_backend())"` 必须回显目标后端名；只看 `hermes config get` 不够（那只证明配置写了，不证明 key 被读到）。
