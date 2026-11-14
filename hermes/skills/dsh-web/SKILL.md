---
name: dsh-web
description: "Use when dsh web（DeepSeek Harness GUI）连不上或要取访问 token"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [dsh, deepseek, harness, web-gui, systemd, troubleshooting]
---

# dsh web（DeepSeek Harness Web GUI）

## When to Use

- 用户说"dsh web 连不上""打不开 dsh""harness 界面没了"
- 需要给用户提供 dsh web 的访问地址（token 每次重启会变）
- dsh-web.service 处于 auto-restart / activating 状态

## 背景

本机 DeepSeek Harness 的 Web 界面，node 启动器（`~/.local/bin/dsh web`），systemd 用户单元 `dsh-web.service`，绑定 **127.0.0.1:3080**。

## 访问

1. 确认服务在跑：`systemctl --user is-active dsh-web.service`
2. 取 token（**每次重启都变**）：
   ```bash
   journalctl --user -u dsh-web.service -n 20 --no-pager | grep token
   # 输出形如: dsh web: http://127.0.0.1:3080/?token=xxxx
   ```
3. 浏览器打开 `http://127.0.0.1:3080/?token=<token>`

注意：无 token 访问返回 HTTP 401，**这是正常鉴权响应，不代表服务挂了**。

## 故障排查（按顺序）

1. `systemctl --user status dsh-web.service --no-pager` — 看 Active 状态
2. 卡 `activating (auto-restart)` → 查 journal：`journalctl --user -u dsh-web.service -n 60 --no-pager`
   - 若见 `Control process exited, code=killed, status=15/TERM` 且重启计数暴涨：`ExecStartPre` 的清理命令自杀了（详见坑 1）
3. 手动跑一次看真实输出：`~/.local/bin/dsh web`（前台，能直接看到启动日志和 token）
4. 修复 unit 后：`systemctl --user daemon-reload && systemctl --user restart dsh-web.service`
5. 验证：`is-active` 返回 `active` + curl 得到 401

## 坑

- **`ExecStartPre` 里 `pkill -f "<pattern>"` 会自杀**：systemd 用 `sh -c 'pkill -f ...'` 执行，该 sh 自身命令行含 pattern → pkill 杀了它，unit 永远起不来、重启计数无限涨。清理残留进程要用 `pgrep -x node -f "^node.*<pattern>"`（精确匹配真实进程）；更干净的方案是 `systemctl --user stop` 按 cgroup 收进程。本机 2026-11-09 踩过，修复已写入 unit。
- **headless 环境加 `--no-open`**：dsh 默认尝试打开默认浏览器，无桌面会话时报错/卡住。unit 的 ExecStart 必须带 `--no-open`。
- **token 不落盘**：只打印在 journal 里，重启即失效，别缓存旧 URL。
- 局域网访问需把 unit 里的 `127.0.0.1` 改为 `0.0.0.0` 并放行防火墙，当前未开放。
