---
name: octop
description: "Deploy and operate the Octop agent platform locally."
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [octop, agent-platform, deployment, deepseek, tencent]
    related_skills: [hermes-agent, web-crud-application]
---

# Octop 本地部署与运维

## When to Use
- 部署 Octop（TencentCloud/Octop）到本机作为团队 agent 服务器。
- 配置 Octop 的 LLM provider（DeepSeek/OpenAI 兼容端点）、创建 agent/用户。
- 调用 Octop 聊天 API（WebSocket）验证功能或写集成。
- 评估 Octop 在单机上的并发能力。

Octop（TencentCloud/Octop）是单进程 asyncio 多用户 agent 平台：Web Dashboard + JWT 多用户隔离 + 共享专家/工具 + AgentTeams。单 uvicorn 进程，SQLite WAL（默认）或 PostgreSQL，只能垂直扩展。用于团队共享 agent 场景时优于 Hermes（Hermes 胜在个人本地模型生态）。

## 并发预期（先给用户的结论）
- 聊天为主（瓶颈是 LLM API，不是 Octop）：约 50–200 并发用户。
- 重工具/AgentTeams 任务：约 5–15 并发。
- 内存基线 ~200–500MB + 每个活跃 agent ~50–200MB；GB10 121GB 统一内存可轻松撑 50–100 个活跃会话（多数时间在等 LLM 返回）。
- 单进程，无 worker 池；要横向扩只能换 PostgreSQL + 多实例（Octop 本身不自动分片）。

## 部署步骤（已验证，DGX Spark / ARM64 / Ubuntu）

```bash
# 1. 独立 venv（别污染 Hermes 或全局环境）
uv venv --python /usr/bin/python3.12 ~/.octop-venv
source ~/.octop-venv/bin/activate

# 2. 安装
uv pip install octop        # 当前 1.0.1
octop --help                # 验证 CLI

# 3. 初始化（首次）
octop init --admin-user admin --admin-password '<强密码>' --force --yes
```

**init 陷阱：**
- `password is too common` —— `admin123` 这类弱密码被拒。用含大小写+数字+符号的强密码，不要把密码明文存进 skill 或 memory。
- `already exists and is not empty` —— 首次失败会留下非空 `~/.octop`；重试时加 `--force` 覆盖。
- 初始化产物在 `~/.octop/`（`config.yaml`、`data.db`、`agents/`、`logs/`）。

## Provider 配置（DeepSeek 为例）

```bash
KEY=$(grep 'DEEPSEEK_API_KEY' ~/.hermes/.env | cut -d= -f2)
octop provider create \
  --name deepseek \
  --kind openai \
  --base-url "https://api.deepseek.com/v1" \
  --api-key "$KEY" \
  --models '[{"id":"deepseek-flash","name":"DeepSeek Flash","context_length":1000000,"max_output_tokens":384000},{"id":"deepseek-v4-pro","name":"DeepSeek V4 Pro","context_length":1000000,"max_output_tokens":384000}]'
octop provider test 2          # 验证连通（~1.6s 正常）
octop models active --provider deepseek --model deepseek-flash
```

**Provider 陷阱：**
- `--kind` 必须用 Octop 内部的 kind 字面量。DeepSeek 走 OpenAI 兼容协议，正确值是 `--kind openai` + `--base-url https://api.deepseek.com/v1`。**不要用 `openai_compatible`**——会创建出 `provider test` 找不到/连不通的脏记录。
- 用错 kind 的记录要 `octop provider delete <id>` 清掉再重建，否则残留坏配置。
- 查支持哪些 preset：`octop models presets --json`。不确定 kind 时读 `site-packages/octop/infra/agents/providers/presets.py` 里的 `provider_template.json` 字段确认 protocol。
- DeepSeek 官方模型 id 只有 `deepseek-flash`（=V4.1-Flash，1M 上下文，多模态）和 `deepseek-v4-pro`；`deepseek-chat`/`deepseek-reasoner` 已退役。

## 创建 Agent

```bash
octop agent experts                        # 看可用专家模板
octop agent create '小通' --template general-assistant --user admin
```

**陷阱：** `agent create` 不显式给 `--user` 会报缺参；`--template` 用 `octop agent experts` 列出的名字。创建后 agent 有短 id（如 `91RCBP`，存在 `agent_id` 字段），聊天/路由用它；REST 列表里的 `id` 是自增主键，别混用。

## 启动服务

```bash
octop run --host 0.0.0.0 --port 8686       # 后台跑
# 验证
curl -s http://127.0.0.1:8686/             # Web UI
ss -tlnp | grep 8686
```

- 服务是前台进程，`octop run` 退出即停。要开机自启需另写 systemd user service（参考 HRMS 的 `~/.config/systemd/user/hrms.service` 模式）。
- **本机已装 user 级 systemd 服务**：`~/.config/systemd/user/octop.service`（`systemctl --user restart octop` 管理）。`Restart=on-failure`，挂了 5s 后自动拉起。
- 默认端口 8686，局域网访问 `http://<本机IP>:8686`。

**自杀陷阱（真实事故）：** agent 拥有宿主的 shell 访问（LocalShellBackend rooted at '/'），让它"服务化/重启不挂"时它的第一步是 kill 当前手动进程——**但它自己就跑在这个进程里，kill 一执行宿主就没了**，systemd unit 永远写不到，且反复被问"装好了吗"会反复自杀。结论：服务化必须由外部（Hermes/人）执行，别派给 Octop agent 自己。另外其 tool_guard 对 `TOOL_CMD_PROCESS_KILL`/`PRIVILEGE_ESCALATION` 只警告不拦截，sudo 需要密码。

## API 调用（验证功能用）

**鉴权端点是 `/api/auth/login`（不是 `/api/v1/auth/login`）**，返回 `access_token`：

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8686/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"<密码>"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -s http://127.0.0.1:8686/api/agents -H "Authorization: Bearer $TOKEN"
curl -s http://127.0.0.1:8686/api/agents/<agent_id> -H "Authorization: Bearer $TOKEN"
```

**聊天走 WebSocket，不是 HTTP POST**（对 `/chat`、`/messages`、`/sse` 等 POST 都返回 `Method Not Allowed`）：

```python
import json, websocket
token = "..."  # 从 /api/auth/login 拿到
ws = websocket.create_connection(f"ws://127.0.0.1:8686/api/agents/<agent_id>/chat/ws?token={token}", timeout=30)
ws.send(json.dumps({"type": "user_turn", "text": "你好"}))
# 循环 ws.recv() 收帧，type 含: token / reasoning / tool_call_chunk / tool_result /
# state_snapshot / state_update / usage / done（done 表示一轮结束）
```

- 一轮正常响应约几百帧；看到 `type: done` 即本轮完成。
- 帧模型定义在 `octop/api/routers/chat/models.py`（`ChatTurnBody`），支持 `thread_id`（复用会话）、`default_model`（如 `deepseek/deepseek-flash`）、`skills`、`mcp_servers`、`target_agent_ids`（@ 其他 agent）。
- 需要 `pip install websocket-client`。
- 想枚举全部路由：`curl http://127.0.0.1:8686/openapi.json` 看 `paths`。

## 管理命令速查

```bash
octop provider list | test <id> | delete <id>
octop models active | presets --json
octop agent list | experts | create | delete
octop user list | create --email x@y.com
octop run --host 0.0.0.0 --port 8686
```

团队用户逐个 `user create` 邮箱，各自用 Web UI 登录，JWT 隔离会话。
