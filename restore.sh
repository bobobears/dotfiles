#!/bin/bash
# ================================================================
# bobobears dotfiles 一键恢复脚本
# 用法：bash restore.sh [--dry-run]
# 在新装 Ubuntu 系统上运行，恢复所有配置
# ================================================================

set -euo pipefail

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

do_cmd() {
    if $DRY_RUN; then
        echo "[DRY-RUN] $*"
    else
        echo "[EXEC] $*"
        "$@"
    fi
}

echo "========================================"
echo "  bobobears Dotfiles Restore"
echo "  Mode: $($DRY_RUN && echo 'DRY RUN' || echo 'LIVE')"
echo "========================================"

# ── 1. 安装系统包 ──────────────────────────────
echo ""
echo "── [1/6] 系统包 ──"
if [ -f "$DIR/packages/dpkg-list.txt" ]; then
    do_cmd sudo apt update
    # 恢复已安装的包列表（注意：这只会安装还在仓库里的）
    # do_cmd sudo dpkg --set-selections < "$DIR/packages/dpkg-list.txt"
    # do_cmd sudo apt dselect-upgrade -y
    echo "  → 参考：cat packages/dpkg-list.txt 看看之前装了哪些包"
fi

# ── 2. Shell 配置 ──────────────────────────────
echo ""
echo "── [2/6] Shell 配置 ──"
for f in .bashrc .profile .gitconfig; do
    [ -f "$DIR/shell/$f" ] && do_cmd cp "$DIR/shell/$f" "$HOME/$f"
done

# ── 3. SSH 配置 ────────────────────────────────
echo ""
echo "── [3/6] SSH 配置 ──"
[ -f "$DIR/ssh/config" ] && do_cmd cp "$DIR/ssh/config" "$HOME/.ssh/config"
for pub in "$DIR/ssh/"*.pub; do
    [ -f "$pub" ] && do_cmd cp "$pub" "$HOME/.ssh/"
done
do_cmd chmod 600 "$HOME/.ssh/config"
do_cmd chmod 644 "$HOME/.ssh/"*.pub

# ── 4. Hermes Agent ────────────────────────────
echo ""
echo "── [4/6] Hermes Agent ──"
if [ -d "$HOME/.hermes" ]; then
    [ -f "$DIR/hermes/config.yaml" ] && do_cmd cp "$DIR/hermes/config.yaml" "$HOME/.hermes/config.yaml"
    [ -f "$DIR/hermes/SOUL.md" ] && do_cmd cp "$DIR/hermes/SOUL.md" "$HOME/.hermes/SOUL.md"
    echo "  → Hermes 技能需重新安装: hermes skill install <name>"
else
    echo "  → ~/.hermes/ 不存在，先安装 Hermes Agent"
fi

# ── 5. GNOME 桌面设置 ─────────────────────────
echo ""
echo "── [5/6] GNOME 桌面设置 ──"
[ -f "$DIR/gnome/gnome-terminal.txt" ] && do_cmd dconf load /org/gnome/terminal/ < "$DIR/gnome/gnome-terminal.txt"

# ── 6. 应用快捷方式 ────────────────────────────
echo ""
echo "── [6/6] 应用快捷方式 ──"
mkdir -p "$HOME/.local/share/applications"
for f in "$DIR/apps/"*.desktop; do
    [ -f "$f" ] && do_cmd cp "$f" "$HOME/.local/share/applications/"
done

echo ""
echo "========================================"
echo "  恢复完成！"
echo "  注意事项："
echo "  - SSH 私钥需要手动复制（未备份）"
echo "  - LM Studio 模型文件需重新下载"
echo "  - apt 包列表仅供参考，手动装："
echo "    cat packages/dpkg-list.txt | awk '{print \$1}'"
echo "========================================"
