---
name: system-backup
description: >-
  Backup Linux system configuration, Hermes Agent (SOUL.md, USER.md, MEMORY.md,
  config.yaml, skills/), SSH keys, dotfiles, and package lists to a GitHub
  dotfiles repository for disaster recovery. Includes a restore.sh script for
  one-command recovery after reinstall.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [backup, dotfiles, disaster-recovery, hermes, linux]
    related_skills: [github-repo-management, github-auth]
---

# System Backup (dotfiles + Hermes)

Back up system configuration files, Hermes Agent identity/memory/skills, SSH
config, and package lists to a GitHub repository. After a reinstall, clone the
repo and run `restore.sh` to get back to a working state.

This is NOT a full disk backup. It backs up configuration, not data files
(models, large projects, downloads). For those, use a separate data partition
(see the guide below) or rsync.

## When to Use

- Before reinstalling the OS
- When setting up a new machine
- When the user asks "how do I back this up" or "save my config"

## Quick Start (for the agent)

```bash
# Create repo
gh repo create <user>/dotfiles --public --source=. --push

# Or if gh isn't available:
# 1. Create via API
gh api --method POST /user/repos -f name=dotfiles -f private=false
# 2. Push from local
cd ~/dotfiles && git remote add origin https://github.com/<user>/dotfiles.git
git push -u origin main
```

## Backup Checklist

### 1. Shell Config
```bash
mkdir -p ~/dotfiles/shell
cp ~/.bashrc ~/dotfiles/shell/
cp ~/.profile ~/dotfiles/shell/
cp ~/.gitconfig ~/dotfiles/shell/
```

### 2. Hermes Agent Config & Persona
```bash
mkdir -p ~/dotfiles/hermes/memories
cp ~/.hermes/config.yaml ~/dotfiles/hermes/
cp ~/.hermes/SOUL.md ~/dotfiles/hermes/
cp ~/.hermes/memories/USER.md ~/dotfiles/hermes/memories/
cp ~/.hermes/memories/MEMORY.md ~/dotfiles/hermes/memories/
# List installed skills (for reference)
ls ~/.hermes/skills/ > ~/dotfiles/hermes/skills-list.txt
```

### 3. All Skills (SKILL.md + scripts + references)
```bash
cp -r ~/.hermes/skills/* ~/dotfiles/hermes/skills/
```
The skills directory may be 5-50MB. Skills with `.git/` or `node_modules/` should
be excluded via `.gitignore` (add `hermes/skills/*/.git/` and `hermes/skills/*/node_modules/`).

### 4. SSH Config (public keys only — NEVER backup private keys)
```bash
mkdir -p ~/dotfiles/ssh
cp ~/.ssh/config ~/dotfiles/ssh/
cp ~/.ssh/*.pub ~/dotfiles/ssh/
```

### 5. Package Lists
```bash
mkdir -p ~/dotfiles/packages
dpkg --get-selections > ~/dotfiles/packages/dpkg-list.txt
snap list 2>/dev/null > ~/dotfiles/packages/snap-list.txt
pip3 list --format=columns 2>/dev/null > ~/dotfiles/packages/pip-global.txt
uv tool list 2>/dev/null > ~/dotfiles/packages/uv-tools.txt
```

### 6. GNOME Desktop Config
```bash
mkdir -p ~/dotfiles/gnome
dconf dump /org/gnome/terminal/ > ~/dotfiles/gnome/gnome-terminal.txt
```

### 7. Application Shortcuts
```bash
mkdir -p ~/dotfiles/apps
cp ~/.local/share/applications/*.desktop ~/dotfiles/apps/ 2>/dev/null
```

### 8. Create restore.sh

A one-command recovery script that:
- Copies dotfiles back to `$HOME`
- Restores Hermes config, SOUL.md, USER.md, MEMORY.md
- Restores skills to `~/.hermes/skills/`
- Restores SSH config and public keys
- Reloads GNOME terminal settings

See the template below for a minimal restore.sh.

## Template: restore.sh

```bash
#!/bin/bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Restoring shell config..."
cp "$DIR/shell/.bashrc" "$HOME/" 2>/dev/null
cp "$DIR/shell/.profile" "$HOME/" 2>/dev/null
cp "$DIR/shell/.gitconfig" "$HOME/" 2>/dev/null

echo "==> Restoring Hermes config..."
mkdir -p "$HOME/.hermes/memories"
cp "$DIR/hermes/config.yaml" "$HOME/.hermes/" 2>/dev/null
cp "$DIR/hermes/SOUL.md" "$HOME/.hermes/" 2>/dev/null
cp "$DIR/hermes/memories/USER.md" "$HOME/.hermes/memories/" 2>/dev/null
cp "$DIR/hermes/memories/MEMORY.md" "$HOME/.hermes/memories/" 2>/dev/null
if [ -d "$DIR/hermes/skills" ]; then
    cp -r "$DIR/hermes/skills/"* "$HOME/.hermes/skills/"
fi

echo "==> Restoring SSH..."
cp "$DIR/ssh/config" "$HOME/.ssh/" 2>/dev/null
for pub in "$DIR/ssh/"*.pub; do [ -f "$pub" ] && cp "$pub" "$HOME/.ssh/"; done
chmod 600 "$HOME/.ssh/config" 2>/dev/null

echo "==> Done!"
echo "Note: SSH private keys must be copied manually (not backed up)."
```

## .gitignore Template

```
# SSH private keys (NEVER backup these)
ssh/id_*
!ssh/id_*.pub

# Hermes logs/cache/sessions
hermes/logs/
hermes/*.bak.*
hermes/skills-output.txt

# Skills internal git repos and node_modules
hermes/skills/*/.git/
hermes/skills/*/node_modules/

# GNOME full dconf dump (too large)
gnome/dconf-full-backup.txt
```

## Pitfalls

- **DNS resolution when pushing:** In China-network environments, `git push` may fail with
  `Temporary failure in name resolution` even when `gh api` works. Fix temporarily:
  `resolvectl dns <interface> 223.5.5.5 114.114.114.114`
- **ghproxy interfering with push:** If `.gitconfig` has `insteadOf https://ghproxy.net/...`,
  remove it for pushes. Use `git -c url.https://github.com/.insteadOf= push` or
  set up SSH remote (`git@github.com:user/repo.git`) instead.
- **SSH private keys should NEVER be backed up to GitHub.** The `.gitignore` must
  exclude `ssh/id_*` while keeping `ssh/id_*.pub` and `ssh/config`.
- **Hermes config.yaml may contain API endpoint URLs.** Review for hardcoded keys
  before committing.
- **Large skill directories** (e.g. skills with many scripts/references) may be
  5-50MB. `git push` handles this fine but the initial commit takes a moment.
- **USER.md and MEMORY.md** live in `~/.hermes/memories/` (capital letters, not `~/.hermes/` directly).

## Layered Backup Strategy

For single-partition systems (no separate `/home` or `/data`), define **two backup
layers**:

| Layer | What | Tool | Target | Frequency |
|-------|------|------|--------|-----------|
| **Config + code** | dotfiles, Hermes config, SSH, package lists, private_db scripts | `git push` | GitHub repo | Weekly |
| **Data + projects** | dsa, hrms, documents, SQLite databases | `rsync` | External drive or FUSE mount | Daily |

The first layer is covered by the checklist above. The second layer is covered
by the companion pattern below.

## Private DB Scripts

Include private database utility scripts from `~/private_db/` in the dotfiles
backup (NOT the `.db` file itself — that's data, not config):

```bash
mkdir -p ~/dotfiles/private_db
cp ~/private_db/db.py ~/dotfiles/private_db/
cp ~/private_db/init_schema.py ~/dotfiles/private_db/
cp ~/private_db/is_trading_day.py ~/dotfiles/private_db/
```

## System Bootstrap Script (中文)

For the DGX Spark single-partition setup where `/home` is on the root
partition, a **dedicated recovery script** (`系统引导.sh`) should live on the
E-drive backup destination. After a reinstall, the user opens the E drive and
runs it.

The script (`E:/系统引导.sh`) performs these steps in order:

| # | Phase | What it does |
|---|-------|-------------|
| 1 | 系统基础 | apt mirror (TUNA), curl/wget/git/htop/tmux |
| 2 | 开发工具链 | Python3/pip/uv, Node.js 20, Docker |
| 3 | Hermes Agent | install via curl, restore SOUL.md + config.yaml |
| 4 | Shell 配置 | .bashrc, .profile, .gitconfig |
| 5 | SSH 配置 | config + public keys from backup |
| 6 | 私人数据库 | restore db.py scripts + latest private.db dump |
| 7 | 项目恢复 | dsa + hrms projects, recreate venvs |
| 8 | GitHub & dotfiles | gh CLI, SSH auth, git clone dotfiles |
| 9 | 收尾 | DNS (223.5.5.5), cleanup |

Key design decisions:
- Uses `--dry-run` flag so the user can preview before executing
- Color-coded output (green/yellow/cyan)
- Each phase is idempotent
- Non-fatal: skips failed phases with a warning
- LM Studio models (119GB) are NOT restored — downloadable on demand
- Double-backed-up: root of E drive + HermesBackup/bootstrap/

The daily backup cron ensures this script is synced every run.

## Companion: Data Backup via FUSE (xrdp Remote Desktop Mapping)

When the only available backup destination is a **Windows drive mapped through
xrdp** (e.g. `~/thinclient_drives/E:/`), the FUSE filesystem has quirks that
break naive `rsync`:

| Quirk | Symptom | Fix |
|-------|---------|-----|
| No symlink support | `rsync: symlink X -> Y failed: Function not implemented (38)` | Use `rsync --copy-links -J` to expand symlinks into real files |
| Deep `mkdir -p` unreliable | rsync destination creation fails | Create each destination dir with a separate `mkdir -p` before rsync |
| `du -sh` hangs | No output returned, fs doesn't support recursive size scans | Use `ls | wc -l` for file counts instead |

### Recommended script skeleton

```bash
#!/bin/bash
# e-drive-backup.sh — 数据备份到 xrdp 映射的 E 盘
# ⚠️ 所有 echo 输出会被原样推送到飞书，必须使用中文
BACKUP_BASE="/home/bobobears/thinclient_drives/E:/HermesBackup"
LOG_FILE="$HOME/.hermes/logs/e-drive-backup.log"

# 1. 挂载检查 — RDP 断连时静默退出
if [ ! -d "/home/bobobears/thinclient_drives/E:" ]; then
    echo "❌ E 盘未挂载（RDP 未连接），备份跳过" && exit 1
fi
mkdir -p "$BACKUP_BASE" || { echo "❌ E 盘不可写，备份跳过" && exit 1; }

# 2. Rsync 封装 — 处理 FUSE 符号链问题
rsync_to_drive() {
    local src="$1" dst="$2"
    rsync -ah --delete --copy-links -J "$src" "$dst" \
        --exclude="__pycache__" --exclude="*.pyc" --exclude=".git" \
        --exclude="node_modules" --exclude=".venv" --exclude="venv" \
        --exclude=".mypy_cache" --exclude=".pytest_cache"
}

# 3. 数据库备份（SQLite 时间点快照）
sqlite3 /path/to/db ".backup $BACKUP_BASE/db/db_$(date +%Y%m%d_%H%M).db"
# 保留 30 天
find "$BACKUP_BASE/db" -name "db_*.db" -mtime +30 -delete

# 4. 项目同步 — 先创建目标目录
for dir in dsa hrms; do
    mkdir -p "$BACKUP_BASE/projects/$dir/current"
    rsync_to_drive "$HOME/$dir/" "$BACKUP_BASE/projects/$dir/current/"
done

# 5. 最终输出（推送到飞书时用户会看到这行）
echo "✅ E 盘备份完成"
```

### Cron setup (no_agent mode)

```bash
hermes cron create \
  --name "E drive data backup" \
  --schedule "0 17 * * *" \
  --script e-drive-backup.sh \
  --no-agent \
  --deliver feishu
```

**⚠️ 陷阱：默认 `--deliver local` 只存不推**

`no_agent=True` 模式的标准输出不会出现在 agent.log 中，也不会推送到任何聊天平台。
- `--deliver local` → 脚本执行结果仅存于 scheduler 内部日志，**用户收不到任何通知**
- 必须显式指定目标，如 `--deliver feishu`、`--deliver all`、`--deliver feishu:chat_id`
- 失败时用户同样收不到通知——脚本成功或失败的输出都会按 `deliver` 目标投递

推荐做法：创建时直接指定目标平台。

### no_agent 脚本注意事项

1. **脚本权限必须 `755` 而非 `711`** — Hermes cron 调度器读取脚本文件需要读权限，而 `chmod 711`（`rwx--x--x`）去掉了文件属主的读权限，导致调度失败。始终使用 `chmod 755 ~/.hermes/scripts/*.sh`。

2. **脚本输出到飞书/微信必须全程中文** — no_agent 脚本的 `echo` 输出会直接原样推送。如果用户使用中文环境，脚本中的状态消息（成功/失败/警告）必须使用中文，否则推送出去用户看不懂。
   - ✅ 正确：`echo "E 盘定期备份已完成 — 数据库和项目文件已同步到 E 盘"`
   - ✅ 正确：`echo "E 盘备份未执行 — RDP 远程桌面未连接，E 盘映射不可用"`
   - ❌ 错误：`echo "DONE"` / `echo "FAIL:mount_not_found"` / `echo "Backup completed"` — 推送后用户看不懂
   - **不要使用 emoji 代替中文**（如 `✅ 备份完成`），纯中文句子比 emoji+简短文字更清晰

3. **cron 投递外壳的中文化（框架层修改）** — Hermes cron 框架在 `scheduler.py` 中生成投递外壳文字，默认是英文：
   ```
   Cronjob Response: {task_name}
   (job_id: {job_id})
   -------------
   ...
   To stop or manage this job, send me a new message (e.g. "stop reminder...").
   ```
   如需改为中文，修改 `~/.hermes/hermes-agent/cron/scheduler.py` 第 1111-1115 行。同时更新 `gateway/platforms/yuanbao.py` 中的 `strip_cron_wrapper()` 方法（约第 4860 和 4871 行），保持 strip 匹配模式与新的中文前缀同步。
   - **⚠️ 修改后必须清 `.pyc` 缓存 + 重启 gateway** 才能生效：
     ```bash
     # 1. 清除缓存
     find ~/.hermes/hermes-agent/cron/__pycache__ -name "scheduler*" -delete
     find ~/.hermes/hermes-agent/gateway/platforms/__pycache__ -name "yuanbao*" -delete
     # 2. 重启 gateway（kill PID，systemd 自动重启）
     kill $(ps aux | grep "hermes_cli.main gateway" | grep -v grep | awk '{print $2}')
     # 3. 确认新进程启动
     sleep 5
     systemctl --user is-active hermes-gateway.service
     ```
   - **Python 进程缓存机制**：修改 `.py` 后，如果 Python 进程不重启，`import` 过的模块不会重新加载。
     即使 `.py` 文件比 `.pyc` 新，Python 也会优先使用已有的 `.pyc` 文件。必须删 `.pyc` 或重启进程。
   - **两个独立进程需要关注**：
     - `hermes-gateway.service`（负责定时任务调度和投递）—— 重启 gateway 后，**下次自动触发的定时任务**会使用新代码
     - `Hermes Desktop` 内的 TUI worker 进程（负责当前对话）—— 如果当前对话手动 `cronjob run`，**当前 worker 进程**的旧模块仍在起作用，需重启 Desktop 主进程
   - **当前会话中无法用 `systemctl --user restart hermes-gateway`**（gateway 会阻止子进程），推荐直接 kill gateway PID，systemd 会自动重启。

## References

See `references/data-backup-patterns.md` for the full xrdp error transcript
and reproduction steps.

## Verification

After backing up, verify:

```bash
cd ~/dotfiles
# 1. Private keys excluded
git check-ignore -q ssh/id_ed25519 || echo "WARNING: private key not ignored!"
# 2. Essential files present
for f in shell/.bashrc shell/.gitconfig hermes/config.yaml hermes/SOUL.md \
         hermes/memories/USER.md hermes/memories/MEMORY.md ssh/config \
         packages/dpkg-list.txt restore.sh; do
  [ -f "$f" ] || echo "MISSING: $f"
done
# 3. No uncommitted changes
git status --porcelain | grep -q . && echo "WARNING: dirty working directory"
# 4. Remote in sync
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || echo "WARNING: push needed"
```

## Data Partition Strategy (Companion)

This skill backs up *configuration*. For *data* (model files, project repos,
downloads), combine with a separate partition layout:

```
nvme0n1p1  298M  /boot/efi     (EFI, keep)
nvme0n1p2  200G  /             (system, format on reinstall)
nvme0n1p3  500G  /home         (dotfiles, configs, projects — keep!)
nvme0n1p4  rest  /data         (models, LM Studio, downloads — keep!)
```

With this layout, reinstalling only formats `/` and `/boot/efi`. `/home` and
`/data` survive untouched. After reinstall, just:
```bash
git clone ... ~/dotfiles && bash ~/dotfiles/restore.sh
```
