---
name: node-package-install
description: "Install npm packages: prerelease, mirror, timeouts."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [npm, node, install, registry, npmmirror]
---

# Node Package Install (本机 Node/npm 包安装)

## When to Use

安装 Node.js / npm 包（含全局 CLI 工具）到本机时，尤其是遇到 ETARGET、registry 同步滞后、安装超时或需要启动常驻 Web 服务时。

## 环境事实

- Node v22.23.0 / npm 10.9.8，全局包装到 `~/.local/bin`（已入 PATH）。
- **默认 registry 是 npmmirror**（`npm config get registry` = https://registry.npmmirror.com），国内直连 registry.npmjs.org 慢。
- pnpm 可用：`~/.hermes/tools/pnpm-*-linux-arm64/pnpm`。

## 流程

1. **先查 registry 再装**：`npm config get registry`。默认走 npmmirror，国内环境一般不用换。
2. **ETARGET / notarget 时查版本分布**：`npm view <pkg> dist-tags` 和 `npm view <pkg> versions`。
   - 若 `latest` 指向 prerelease（如 `0.2.2-rc.1`），裸装 `npm i -g <pkg>` 会报 `No matching version found for <pkg>@*` —— npm 的 `*` 不匹配 prerelease 版本，**必须显式写 `@latest` 或具体版本号**。
3. **镜像没有该版本时**（npmmirror 同步滞后）：`npm view <pkg> dist-tags --registry=https://registry.npmjs.org` 确认官方源有，再决定直连。
4. **大包装装超时的处理**：
   - 先试默认镜像（npmmirror 快）。
   - 镜像上没有 → 直连 npmjs，**terminal timeout 给 600s**；仍超时改 `terminal(background=true)` 装完再验证。
   - 一次失败先看 dist-tags 再决策，不要反复在两个 registry 之间切换重试。
5. **装完立即验证**：`which <cmd>` + `<cmd> --version`，再跑 `--help` 确认入口可执行。
6. **需要常驻的 Web 服务**（如 `dsh web`）：`terminal(background=true, notify=true)` 启动，`ss -tlnp | grep <pid>` 找监听端口（dsh web 默认 127.0.0.1:3080，带随机 token，URL 从进程日志取）。

## 坑

- **prerelease 不匹配 `*`**：`latest` = prerelease 时裸装必挂，显式 `@latest`。
- **npmmirror 同步滞后**：新包或新版本可能只有 npmjs 源有；两个源都 `npm view <pkg> versions --registry=...` 查一遍再下结论。
- **npmjs 直连慢**：国内 7 分钟+ 超时常见，大依赖树优先镜像；镜像真没有才直连 + background。
- **带鉴权的本地服务**：`dsh web` 返回 401 是预期行为（token 鉴权），从进程日志拿完整 URL，不要误判为故障。
- **terminal 里 `cmd &` 会被拒**：需要后台就用 `terminal(background=true)`，不要 shell 内 `&`。
