---
name: dotfiles-backup
description: "备份关键系统配置到 GitHub dotfiles 仓库：shell 配置、Hermes Agent（config/SOUL/USER/MEMORY/skills）、SSH 公钥、包清单、GNOME 桌面设置"
version: 1.0.0
author: Hermes
platforms: [linux]
dependencies: [gh, git]
prerequisites:
  commands: [gh, git]
metadata:
  hermes:
    tags: [backup, dotfiles, hermes-config, system-config]
---

# dotfiles-backup

## Overview

将当前系统的关键配置增量备份到 `~/dotfiles` 目录并推送到 GitHub `bobobears/dotfiles` 仓库。用于系统重装后快速恢复开发环境。

## When to use

- 定期备份（建议每周一次）—— 另见 `system-backup` 技能获取分层备份方案
- 系统重装前确保所有配置已备份
- 安装了新的 Hermes 技能后
- 修改了 shell/Hermes/SSH 等重要配置后

## Workflow

### 1. 备份 Shell 配置

```bash
cp ~/.bashrc ~/dotfiles/shell/
cp ~/.profile ~/dotfiles/shell/
cp ~/.gitconfig ~/dotfiles/shell/
```

### 2. 备份 Hermes Agent

```bash
# 核心配置 + 人格设定
cp ~/.hermes/config.yaml ~/dotfiles/hermes/
cp ~/.hermes/SOUL.md ~/dotfiles/hermes/

# 持久记忆
mkdir -p ~/dotfiles/hermes/memories
cp ~/.hermes/memories/USER.md ~/dotfiles/hermes/memories/
cp ~/.hermes/memories/MEMORY.md ~/dotfiles/hermes/memories/

# 技能列表（用于参考）
ls ~/.hermes/skills/ > ~/dotfiles/hermes/skills-list.txt

# 完整技能目录（SKILL.md + 脚本/模板/资源）
cp -r ~/.hermes/skills/* ~/dotfiles/hermes/skills/
```

### 3. 备份 SSH 配置

```bash
cp ~/.ssh/config ~/dotfiles/ssh/
cp ~/.ssh/*.pub ~/dotfiles/ssh/
```

> ⚠️ 不备份私钥（`id_*` 不包含 `.pub` 后缀的文件），.gitignore 已忽略

### 3.5 备份私人数据库脚本

```bash
mkdir -p ~/dotfiles/private_db
cp ~/private_db/db.py ~/dotfiles/private_db/
cp ~/private_db/init_schema.py ~/dotfiles/private_db/
cp ~/private_db/is_trading_day.py ~/dotfiles/private_db/
cp ~/private_db/save_dsa_scores.py ~/dotfiles/private_db/
```

> ⚠️ 不备份 .db 文件本身（体积变化大、含业务数据），只备份工具脚本

### 4. 备份系统包清单

```bash
dpkg --get-selections > ~/dotfiles/packages/dpkg-list.txt
pip3 list --format=columns > ~/dotfiles/packages/pip-global.txt
snap list > ~/dotfiles/packages/snap-list.txt 2>/dev/null
uv tool list > ~/dotfiles/packages/uv-tools.txt 2>/dev/null
```

### 5. 备份 GNOME 桌面设置

```bash
dconf dump /org/gnome/terminal/ > ~/dotfiles/gnome/gnome-terminal.txt
cp ~/.local/share/applications/*.desktop ~/dotfiles/apps/ 2>/dev/null
```

### 6. 更新 restore.sh 时间戳（如有必要）

如果 restore.sh 需要更新，手动编辑 ~/dotfiles/restore.sh。

### 7. 提交并推送

```bash
cd ~/dotfiles
git add -A
git commit -m "chore: dotfiles auto-backup $(date +%Y-%m-%d_%H:%M)"
git push
```

## Verification

```bash
cd ~/dotfiles
git status          # 应显示 "nothing to commit, working tree clean"
git rev-parse HEAD  # 记下最新的 commit SHA
```

## Pitfalls

- **DNS 解析失败（有 sudo）**：如果 `git push github.com` 报解析错误，先配置公共 DNS：
  ```bash
  resolvectl dns enP7s7 223.5.5.5 114.114.114.114 8.8.8.8
  ```
- **DNS 解析失败（无 sudo / cron 环境）**：在没有 sudo 权限的 cron 任务中，先检查 `getent hosts github.com` 是否命中缓存：
  - **缓存命中**（返回了 IP）：直接 SSH 推送，SSH 绕过 DNS 直连
  - **缓存未命中**：`ping -c 1 8.8.8.8` 确认网络连通性，然后尝试通过 HTTPS 用裸 IP 远程（需要安全扫描放行）：
    ```bash
    git remote set-url origin https://20.205.243.166/bobobears/dotfiles.git
    git push
    ```
    推送成功后务必恢复 remote：
    ```bash
    git remote set-url origin git@github.com:bobobears/dotfiles.git
    ```
- **SSH 推送失败**：如果 SSH 密钥有问题，改用 HTTPS 推送：
  ```bash
  git remote set-url origin https://github.com/bobobears/dotfiles.git
  git push
  ```
- **ghproxy 劫持 + DNS 双重失效**：`.gitconfig` 中如果包含 `insteadOf = https://github.com/` 指向 ghproxy，在 ghproxy 域名也解析失败时 HTTPS 和 SSH 路径都会断。本地 `.gitconfig` 中的 ghproxy 配置应尽早移除——性能提升有限，但增加了一个脆弱的依赖点。移除方法：
  ```bash
  git config --global --unset url."https://ghproxy.net/https://github.com/".insteadOf
  ```
- **技能数量变化**：备份技能时如果新增/删除了技能，`skills-list.txt` 会自动更新
