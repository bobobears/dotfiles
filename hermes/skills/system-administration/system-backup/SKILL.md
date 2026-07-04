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
