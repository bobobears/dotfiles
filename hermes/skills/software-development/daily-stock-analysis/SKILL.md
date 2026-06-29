---
name: daily-stock-analysis
description: 部署 ZhuLinsen/daily_stock_analysis 股票智能分析系统（49k+⭐），含硅基流动 LLM、Tushare 数据源配置、Web 服务、飞书推送和每日定时分析
---

# 股票智能分析系统 (Daily Stock Analysis) 部署指南

部署 [ZhuLinsen/daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis)（49k+⭐）—— LLM 驱动的多市场股票智能分析系统。

## 前提条件

- Python 3.10+
- git / aria2c（网络慢时 aria2c 比 git clone 更可靠）
- Docker（可选，但国内网络 Docker Hub 可能连不上）
- API 密钥：大模型 API（推荐硅基流动）+ 可选 Tushare Token

## 国内网络特殊处理

GitHub 在国内下载很慢（~30KB/s），raw.githubusercontent.com DNS 被污染。

### 下载策略
- **小文件** (< 200KB)：GitHub API (`api.github.com/repos/.../contents/`) 速度快
- **中等文件**：使用 `ghproxy.net` 代理 `raw.githubusercontent.com` 的 raw 内容
  ```bash
  curl -sL "https://ghproxy.net/https://raw.githubusercontent.com/owner/repo/main/path" -o local_file
  ```
- **大文件** (> 1MB)：用 `aria2c -x 8 -s 8` 多线程下载 GitHub release/archive
- **完整 repo**：先用 `aria2c` 下载 zip，提取后补缺（zip 可能截断）
- **pip install git+https://...**：常因网络超时失败，不推荐
- **Docker pull**：国内 Docker Hub 常超时

### 从截断 ZIP 中提取文件
GitHub archive zip 使用 `store` 压缩（无压缩），截断后可用 Python 手动解析 local file headers 提取已下载的文件：
```python
import struct
# 扫描 PK\x03\x04 标记，解析 local file header 提取每个文件
```

## 部署步骤

### 1. 获取项目树（通过 GitHub API，速度快）
```bash
curl -s "https://api.github.com/repos/ZhuLinsen/daily_stock_analysis/git/trees/main?recursive=1" \
  -H "Accept: application/vnd.github.v3+json" -o repo_tree.json
```

### 2. 下载源码（按需下载，避免 85MB 全量下载）
- 源码仅 ~5MB（206+ Python 文件），其余为文档 assets
- 关键文件：`main.py`, `server.py`, `requirements.txt`, `src/`, `api/`, `bot/`, `data_provider/`, `docker/`
- 使用 GitHub API 或 ghproxy.net 逐文件下载

### 3. 安装依赖
```bash
cd ~/dsa
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. 配置 .env 环境变量
关键配置变量：
```bash
# 自选股列表（沪深代码，逗号分隔）
STOCK_LIST=600519,300750,002594
```
> **💡 修改自选股**：编辑 `.env` 中 `STOCK_LIST` 即可。系统每次定时运行前会自动通过 `config.refresh_stock_list()` 热加载最新列表，**无需重启服务**。详见 `main.py:659-664` 的 Issue #529 hot-reload 逻辑。

```bash
# LLM 配置（硅基流动示例）
LLM_SILICONFLOW_PROTOCOL=openai
LLM_SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
LLM_SILICONFLOW_API_KEY=sk-xxx...n
# 必须设置 LITELLM_MODEL，否则会回退到默认的 gpt-5.5（不存在）
LITELLM_MODEL=openai/deepseek-ai/DeepSeek-V3
LLM_SILICONFLOW_MODELS=deepseek-ai/DeepSeek-V3
LLM_SILICONFLOW_ENABLED=true

# 数据源
TUSHARE_TOKEN=xxx  # 可选，免费版即可

# 推送（可选）
# FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
# WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
```

LLM_CHANNELS 格式说明：
```
LLM_CHANNELS=channel_name1,channel_name2
LLM_{NAME}_PROTOCOL=openai
LLM_{NAME}_BASE_URL=https://...
LLM_{NAME}_API_KEY=sk-xxx
LLM_{NAME}_MODELS=model_name
```

### 5. 启动服务
```bash
cd ~/dsa && source venv/bin/activate
python server.py   # FastAPI Web 服务, http://localhost:8000
```

### 6. 运行分析
```bash
cd ~/dsa && source venv/bin/activate
python main.py
```
报告保存到 `reports/report_YYYYMMDD.md`

### 7. 设置定时任务（Hermes Cron）

使用 Hermes 的 cronjob 工具：
```
每天 9:00 自动运行 python main.py，读取报告，摘要后推送到飞书
```
关键参数：
- schedule: `0 9 * * *`
- deliver: `all`（推送到所有已连接渠道，含飞书网关）
- workdir: `/home/bobobears/dsa`
- prompt: 运行分析 + 读取报告 + 中文摘要

## 验证
- 健康检查：`curl http://localhost:8000/health` → `{"status":"ok"}`
- 日志：`logs/stock_analysis_YYYYMMDD.log`

## 附加数据源（成功经验）

除了 DSA 系统内置的数据源（Tushare/Tencent/AkShare），还发现以下两个可靠的数据提取方式：

### 1️⃣ 通达信 .day 日线文件解析（通过磁盘映射）

**前提**：电脑端安装了华安/华泰等通达信版证券软件，且有磁盘映射（`thinclient_drives`）。

**数据路径格式**：
```
/home/bobobears/thinclient_drives/E:/zd_hazq_gm/vipdoc/{sz,sh}/lday/{code}.day
```

- `sz` = 深交所，`sh` = 上交所
- `{code}` = 6位股票代码，如 `sz002039.day`

**.day 文件格式**（通达信标准，每条 32 字节）：
| 偏移 | 类型 | 内容 |
|:----:|:----:|:-----|
| 0-3 | int32 | 日期（YYYYMMDD，如 20260529） |
| 4-7 | int32 | 开盘价 × 100 |
| 8-11 | int32 | 最高价 × 100 |
| 12-15 | int32 | 最低价 × 100 |
| 16-19 | int32 | 收盘价 × 100 |
| 20-23 | float | 成交额（元） |
| 24-27 | int32 | 成交量（股） |
| 28-31 | int32 | 保留字段 |

**解析代码**（Python struct）：
```python
import struct

filepath = "/home/bobobears/thinclient_drives/E:/zd_hazq_gm/vipdoc/sz/lday/sz002039.day"
record_size = 32

with open(filepath, "rb") as f:
    data = f.read()

num_records = len(data) // record_size
records = []
for i in range(num_records):
    offset = i * record_size
    rec = data[offset:offset+record_size]
    date_val, open_p, high_p, low_p, close_p, amount, volume, reserved = \
        struct.unpack("<iiiiifii", rec)
    year, month, day = date_val // 10000, (date_val % 10000) // 100, date_val % 100
    open_f, close_f = open_p / 100.0, close_p / 100.0
    vol_hands = volume / 100  # 手
    records.append((year, month, day, open_f, close_f, amount, vol_hands))
```

**用途**：离线数据不依赖网络、延迟最低，可精确到每个交易日的开/高/低/收/量，用于股价异常跳空分析、除权除息缺口检测等。

**可以计算的指标**：
- 日涨跌幅：`(close_f / prev_close - 1) * 100`
- 跳空缺口：`(open_f / prev_close - 1) * 100`（<-2% 为跳空低开，>2% 为跳空高开）
- 阶段涨跌：首日收盘 vs 末日收盘
- 阶段最高/最低价
- 从高点回落幅度

### 2️⃣ 东方财富公告 API

**公告列表**（获取最新 N 条公告）：
```python
import urllib.request, json

url = "https://np-anotice-stock.eastmoney.com/api/security/ann" \
      "?sr=-1&page_size=10&page_index=1&ann_type=A" \
      "&stock_list=002039&f_node=0&s_node=0"

req = urllib.request.Request(url, headers={
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://data.eastmoney.com/"
})
resp = urllib.request.urlopen(req, timeout=10)
data = json.loads(resp.read())
items = data.get('data', {}).get('list', [])

for a in items:
    title = a.get('title_ch', '')
    date = a.get('display_time', '')
    columns = [c.get('column_name','') for c in a.get('columns',[])]
    print(f"[{date}] {title}  |  类型: {', '.join(columns)}")
```

**公告详情**（需从列表中获得 `art_code`）：
```python
url = f"https://np-anotice-stock.eastmoney.com/api/security/ann/detail" \
      f"?art_code={art_code}&stock_code={stock_code}"
```

**分红送配数据**（东方财富数据中心 API）：
```python
url = "https://datacenter.eastmoney.com/securities/api/data/v1/get" \
      "?reportName=RPT_F10_FHPS_HFCFH&columns=ALL" \
      "&filter=(SECUCODE=%22SZ002039%22)" \
      "&pageNumber=1&pageSize=5&sortTypes=-1&sortColumns=PLAN_NOTICE_DATE"
```
返回字段：`PLAN_NOTICE_DATE`（公告日）、`RECORD_DATE`（股权登记日）、`EX_DIVIDEND_DATE`（除权除息日）、`DIVIDEND`（每10股派息）、`BONUS`（每10股送股）。

**⚠️ 注意**：东方财富 API 可能因 DNS 污染（open.feishu.cn 类似问题）或网络波动临时断连。出现 `Temporary failure in name resolution` 时，可：
- 检查 `/etc/hosts` 中 datacenter.eastmoney.com / np-anotice-stock.eastmoney.com 的静态 IP
- 或切换至 Tushare 的 `dividend` 接口作为备选

## 常见问题
- **raw.githubusercontent.com 连接失败**：DNS 被污染到 0.0.0.0，必须走 ghproxy.net 代理
- **GitHub API rate limit**：未认证 60次/小时，可通过 API 获取单个小文件
- **ZIP 截断**：GitHub archive 是 store 格式，不完整时可用 local file header 手动提取
- **东方财富接口断连**：因网络波动，系统会自动切换数据源（Tushare → Tencent → AkShare）
- **服务器启动失败**：检查缺失的 .py 文件（ModuleNotFoundError），用 ghproxy 补下
