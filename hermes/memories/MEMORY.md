LAN subnet: 192.168.31.0/24, router: 192.168.31.1 (Xiaomi/XiaoQiang), Dell machine: 192.168.31.113, this machine: 192.168.31.149
§
GitHub: gh CLI 已安装 (v2.45.0), 已登录 bobobears, API配额5000次/h, gh已设git认证
§
中国网络加速: ghproxy.net 代理 GitHub raw 下载/zip/git clone；hf-mirror.com 代理 HF API/模型搜索下载；aria2c -x 4 用于大型 GitHub zip。raw.githubusercontent.com DNS 污染必须走 ghproxy。API 端点 api.github.com 不要走 ghproxy（直接可达，ghproxy 也不适用于 API）。GitHub API 未认证 60次/h，认证后 5000次/h。gh 未安装，SSH 密钥丢失。
§
Git 用户: name=60591511, email=605391511@qq.com
§
新技能安全审计规则：创建或安装任何新技能后，必须用 security-audit 的 audit_skills.py 审计该技能，确认无 HIGH/MEDIUM 安全问题后才算完成。发现问题的必须先修复再交付。
§
Hermes Desktop 启动修复：升级后桌面图标双击无反应，原因是 apps/desktop/release/linux-arm64-unpacked/chrome-sandbox 缺少 SUID root 权限。修复命令：sudo chown root:root <path>/chrome-sandbox && sudo chmod 4755 <path>/chrome-sandbox
§
Weixin/微信已通过 Hermes Gateway (iLink Bot) 连接，DM pairing，群聊 disabled。systemd user service 运行中。
§
飞书已通过 Hermes Gateway 连接 (App ID: cli_aabe74606538dcc7)，DM pairing，群聊 @mentioned only。
§
BBDown ~/.local/bin/BBDown v1.6.3 arm64. Whisper 环境 ~/whisper-env/ CUDA GPU. 见 skill media/bilibili-content。
§
用户: A股长线投资者，偏好国内服务(硅基流动/Tushare/飞书)。DSA项目 /home/bobobears/dsa/ 已部署(206 py文件)，硅基流动+ Tushare API已配置，等待飞书Webhook配推送。
§
飞书DNS修复：open.feishu.cn 间歇性 DNS 解析失败 (小米路由器192.168.31.1不稳定)。修复：1) /etc/hosts 添加 open.feishu.cn 静态IP (117.68.90.117, 60.169.2.33, 223.242.32.17)；2) /etc/systemd/resolved.conf.d/dns-servers.conf 添加公共DNS (223.5.5.5, 114.114.114.114)
§
HuggingFace 国内镜像: hf-mirror.com 可访问 HF API (GET /api/models?search=...) 和模型下载。ghproxy 不能代理 hf.co。hf-mirror.com 比 ghproxy 更快更稳定。
§
DGX Spark GB10 = Blackwell arch (not Hopper), requires CUDA 13+. No CUDA12 available. LM Studio CUDA13 backend stable for models ≤65GB on this 80GB unified system. IOMMU crash threshold ≈80GB model on 80GB total memory. Q3_K_M (64.65GB) of Nemotron-3-Super-120B is the sweet spot for CUDA.
§
本地部署配置: 主模型=LM Studio Qwen (http://127.0.0.1:1234/v1, qwen/qwen3.5-35b-a3b) 日常/重复任务; 委托模型=DeepSeek (deepseek-v4-flash) 复杂任务
§
模型策略: 默认保持 DeepSeek 作为网关和生产稳定 provider。本地 LM Studio Qwen (http://127.0.0.1:1234/v1) 只在用户明确指令切换时才启用，切换后需要先从外部终端重启网关恢复 DeepSeek。