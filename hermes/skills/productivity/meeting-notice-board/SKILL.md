---
name: meeting-notice-board
description: "Use when 发会议通知或维护会议通知发布台 App。局域网填表→企微群+个人。"
version: 1.0.0
author: Hermes (for BoboBears)
metadata:
  hermes:
    tags: [wecom, meeting-notice, fastapi, lan, internal-tool, notification]
---

# 会议通知发布台

## 是什么

局域网内的一张表单；提交后自动把会议通知发布到**企业微信群**，并按勾选推送**个人企业微信**。

| 项 | 值 |
|---|---|
| 访问地址 | `http://192.168.31.149:8077`（局域网） |
| 项目目录 | `~/meeting_notice/` |
| 常驻服务 | `systemctl --user {status,restart} meeting-notice`（enabled + linger） |
| 数据库 | `~/meeting_notice/db/notice.db`（notices / send_logs / members） |
| 日志 | `journalctl --user -u meeting-notice -f` |

## 核心事实：企微推送到哪、需要什么

| 目标 | 接口 | 凭据 | 公网 |
|---|---|---|---|
| **群** | 群机器人 Webhook（`msgtype: markdown`） | 群 → 设置 → 消息推送 → 添加自定义 → Webhook 地址 | ❌ 纯出站 |
| **个人** | 自建应用 `message/send`（`msgtype: textcard`） | CorpID + AgentId + Secret，**且接收人必须在应用可见范围** | ❌ 纯出站 |

- **智能机器人（`WECOM_BOT_ID`/`WECOM_SECRET`）不能主动推送**：群内只能被动回复（需 `req_id` 回执窗口）；DM 只能回已配对用户。做会议通知必须用上面两条通道 —— 这是最容易踩空的前提。
- **@所有人**：群机器人 markdown **不支持** `@all`，必须另发一条 `msgtype: text` + `text.mentioned_list: ["@all"]`。本项目已实现（`wecom.send_group_text`）。
- 应用消息频率：同一人 ≤30 条/分钟；企业未认证时成员上限 100 人。

## 凭据放哪

写进 `~/.hermes/.env`（本应用会读取），或本项目 `.env` 覆盖同名键：

```
WECOM_GROUP_WEBHOOK=
WECOM_CORPID=
WECOM_AGENTID=
WECOM_APP_SECRET=
```

改完 `systemctl --user restart meeting-notice`。**凭据不要贴进对话**。

## 日常操作

| 要做的事 | 怎么做 |
|---|---|
| 发通知 | 首页 → 「发通知」 → 填主题/时间/地点 → 勾选参会人 → 提交 |
| 补人员名单 | `人员` 页：手工加 / 批量粘贴 `姓名,userid,科室` / 「从通讯录同步」 |
| 重发 | 通知详情页 → 「重新发送」 |
| 通道自检 | `人员` 页底部 → 「连接自检」（实发一条群消息 + 校验 token） |

`userid` 取法：管理后台 → 通讯录，或直接用应用凭据调 `user/list`（本应用的「从通讯录同步」按钮就是这么做的）。

## 排障

| 现象 | 原因 |
|---|---|
| 个人通知失败，含 `invaliduser` | 接收人不在自建应用可见范围 |
| 个人通知失败，提示「未配置」 | `WECOM_CORPID`/`WECOM_AGENTID`/`WECOM_APP_SECRET` 缺失 |
| `errcode=40013 invalid corpid` | CorpID 填错（不是企业简称） |
| `errcode=60011` 或无权限 | 自建应用未开通该接口权限 / 可见范围不对 |
| 群里收不到 | Webhook 缺失或被移除；消息类型与载荷不匹配 |
| 局域网打不开 | ① `systemctl --user status meeting-notice` ② 防火墙放行 `sudo ufw allow 8077/tcp` ③ 是否同一网段 |

## 坑（都是实际踩过的）

- **端口别用 8000**：HRMS 占着。本项目固定 **8077**。
- **不要用 `fastapi.templating.Jinja2Templates`**：Starlette 版本不兼容会报 `unhashable type: 'dict'`，直接用原生 `jinja2.Environment` + `HTMLResponse`。
- **模板里读 SQLite 行用 `m['name']`**，不要用 `m.name`（dict 属性访问不可靠）。
- **任何通道失败都必须写 `send_logs`**：静默丢弃会让同事以为通知已发出 —— 这比报错危险得多。
- **改 `.env` 后必须重启服务**：`config.py` 在模块导入时只读一次。
- **群内通知要能证明送达**：靠「自检」按钮实发一条，别只看接口返回 0。
- 服务 `Restart=on-failure` 自愈；配 `loginctl enable-linger <user>` 保证重启后未登录也自启。

## 从零重建

```bash
mkdir -p ~/meeting_notice/{app/templates,db}
cd ~/meeting_notice
python3 -m venv venv
venv/bin/pip install fastapi uvicorn aiosqlite jinja2 python-multipart
# 放入 app/{__init__,config,db,wecom,main}.py 与 app/templates/*.html
systemctl --user enable --now meeting-notice
```
