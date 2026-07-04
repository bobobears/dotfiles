# 持久知识库 (Persistent Knowledge)

> 这个文件是 Hermes 的"长期记忆"，记录环境配置、工具用法、修复方案等不会被频繁改变的稳定事实。
> 与 memory tool 的区别：memory 存的偏"快速事实"（偏好、小技巧），MEMORY.md 更偏向"参考手册"。

---

## 1. 网络环境

### 局域网 (LAN)
- 网段：`192.168.31.0/24`
- 网关：`192.168.31.1`
- 本机（DGX Spark）：`192.168.31.149`
- Dell 机器：`192.168.31.113`

### 代理 & 镜像

| 服务 | 代理方式 | 用途 |
|------|---------|------|
| GitHub | ghproxy.com | raw 文件、zip 下载、git clone |
| HuggingFace | hf-mirror.com | HF API 查询、模型下载（比 ghproxy 更快更稳定） |

> ⚠️ ghproxy 不能代理 hf.co 域名

### 飞书 DNS 修复
- 将 `open.feishu.cn` 静态 IP 写入 `/etc/hosts`
- 系统 DNS 设为 `223.5.5.5` / `114.114.114.114`（阿里 DNS）

---

## 2. Hermes Agent 配置

### 模型策略

```
生产主力: DeepSeek (deepseek-v4-flash) — 默认 provider
本地实验: LM Studio Qwen (http://127.0.0.1:1234/v1, qwen/qwen3.5-35b-a3b) — 仅用户明确指令时切换
重要: 切到本地 Qwen 后，需要从外部终端重启 gateway 才能恢复 DeepSeek
```

### Gateway 状态

| 平台 | App ID / Bot | 配对方式 | 状态 |
|------|-------------|---------|------|
| 飞书 | cli_aabe74606538dcc7 | DM | ✅ 群聊 @mentioned only |
| 微信 | iLink Bot | DM pairing | ✅ 群聊 disabled |

- Gateway 作为 systemd user service 运行

### 桌面版修复
```
Hermes Desktop 升级后若 chrome-sandbox 权限问题：
sudo chown root:root chrome-sandbox && sudo chmod 4755 chrome-sandbox
（在 Hermes Desktop 安装目录下）
```

### DGX Spark (GB10) 限制
- 架构：Blackwell, ARM64
- CUDA 版本支持：CUDA 13+ 以上
- 内存：80GB 统一内存
- 最大可运行模型：Q3_K_M (64.65GB) 的 Nemotron-3-120B

---

## 3. 项目 & 代码

### DSA 项目
- 路径：`/home/bobobears/dsa/`
- 规模：206 个 Python 文件
- API 配置：硅基流动 (SiliconFlow) + Tushare
- 当前状态：已部署，等待飞书 Webhook 推送配置

### 私人数据库
- 路径：`~/private_db/private.db`
- 引擎：SQLite
- 操作命令：`cd ~/private_db && python3 db.py <参数>`
- 支持子命令：`watchlist`、`scores`、`trades`、`notes`、`sql`、`backup`

### DSA 每日评分自动写入
- 脚本：`~/private_db/save_dsa_scores.py`
- 定时：每天 9:00（cron: c1da698090bf）
- 流程：先检查交易日 → 跑 main.py → 写入评分
- 推送：仅发飞书（oc_0ceccf7646b77e9bde35e360953fe805），不发微信

### dotfiles 备份
- 仓库：`bobobears/dotfiles`
- 定时：每周六 17:00（cron: 61dd31d23087）
- 关联技能：`dotfiles-backup`
- 备份内容：shell 配置、Hermes (config + SOUL + memories + skills)、SSH 公钥、包清单、GNOME 配置

---

## 4. 工具 & 技能

### BBDown（B 站下载）
- 路径：`~/.local/bin/BBDown`
- 版本：v1.6.3
- 架构：ARM64
- 关联技能：`media/bilibili-content`

### Whisper（语音转写）
- 环境：`~/whisper-env/`
- 加速：CUDA GPU
- 用途：B 站视频语音转文字

---

## 5. 安全 & 规范

### 新技能安全审计
```
任何新建或安装的 skill，创建/安装后必须立即：
1. 用 security-audit 的 audit_skills.py 审计该技能
2. 确认无 HIGH/MEDIUM 安全问题
3. 发现问题必须先修复再交付
```

### Git 认证
- 邮箱：60591511@qq.com
- 认证方式：gh CLI

### 版本管理规范
- 个人项目使用 conventional commits
- 所有提交前应检查安全性

---

## 6. 备份文件清单参考

| 类别 | 路径/内容 |
|------|----------|
| Shell 配置 | ~/.bashrc, ~/.zshrc, ~/.config/fish/ |
| Hermes 全局 | ~/.hermes/config.yaml, .env, SOUL.md |
| Hermes 记忆 | ~/.hermes/memories/ |
| Hermes 技能 | ~/.hermes/skills/ |
| SSH 密钥 | ~/.ssh/id_*.pub |
| 包清单 | pip list / apt list --installed |
| GNOME 配置 | dconf dump / |
| 私人数据库 | ~/private_db/ |

---

*最后更新：2026-07-04*
