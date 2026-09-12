# 系统引导恢复脚本参考

## 位置

- 主副本：`E:/系统引导.sh`
- 备份副本：`E:/HermesBackup/projects/bootstrap/系统引导.sh`
- 源代码：`/home/bobobears/thinclient_drives/E:/系统引导.sh`
- 示例恢复脚本（dotfiles）：`~/dotfiles/restore.sh`

## 重装后的操作顺序

1. 插上 DGX Spark 电源，连好网线
2. 通过远程桌面（RDP）连接
3. 打开 E 盘 → 找到 `系统引导.sh`
4. 先预览：`bash 系统引导.sh --dry-run`
5. 直接跑：`bash 系统引导.sh`
6. 根据最后输出的"还需要手动做的"清单完成收尾

## 依赖的工具

恢复脚本会主动安装：curl, wget, git, htop, tmux, vim, build-essential, unzip,
python3-pip, python3-venv, nodejs, docker, gh, uv（通过 install.sh）

## 不会自动做的

| 项目 | 原因 |
|------|------|
| SSH 私钥 | 未备份，需手动从加密包恢复 |
| LM Studio 模型 | 119GB，可重下 |
| 飞书 Webhook 配置 | 手动在 Hermes 中配置 |
| cron 任务 | `hermes cron list` 查看后重新注册 |
| Python venv 重建 | 脚本尝试 `uv venv`，失败则提示手动 |

## 从 dotfiles restore.sh 恢复的替代方案

如果 E 盘不可用但 dotfiles GitHub 仓库可访问：

```bash
gh auth login
git clone git@github.com:bobobears/dotfiles.git ~/dotfiles
bash ~/dotfiles/restore.sh
```

dotfiles 恢复的局限：没有 private.db 数据，没有 claude 项目文件。
E 盘 `系统引导.sh` 是完整恢复方案。
