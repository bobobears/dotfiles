# Git 快照 + 回溯 — 状态备份工作流

为 FastAPI + SQLite Web CRUD 项目（如 HRMS）建立「重要变动可回溯」机制。

## 仓库初始化

```bash
cd ~/项目目录
git init
git branch -m main
```

**`.gitignore` 配置**：

```
venv/
__pycache__/
*.py[cod]
db/hrms.db          # 数据库文件不常规跟踪（由快照脚本管理）
snapshots/*/hrms.db
```

## 快照脚本 (`snapshot.sh`)

```bash
./snapshot.sh "描述标签"     # 一键快照
./snapshot.sh list           # 查看历史
./snapshot.sh show <标签>     # 查看详情
```

**关键设计**：

- **数据库与代码共同备份**：`hrms.db` 不纳入 Git 常规跟踪，改用 `cp` 到 `snapshots/YYYYMMDD_HHMMSS/hrms.db` 目录
- **标签名纯 ASCII + 时序编号**：`snapshot-20260709_125440-s02`，避免中文字符
- 标签的描述写入 `git tag -m "描述"`（带 annotation）
- `snapshots/` 目录通过 `.gitkeep` 被 Git 跟踪目录结构，但 `hrms.db` 被 `.gitignore` 排除

## 回溯脚本 (`rollback.sh`)

```bash
./rollback.sh list                    # 列出所有快照
./rollback.sh show <标签名>            # 预览回滚影响
./rollback.sh <标签名>                 # 回滚代码+数据库
./rollback.sh last                     # 回滚到上一个快照
```

**安全机制**：

- 回滚前自动备份当前状态到 `rollback_before_<时间戳>` 标签
- `git reset --hard <标签>` 回滚代码
- 从标签名提取时间戳，找到对应 `snapshots/<时间戳>/hrms.db` 恢复数据库
- 执行前 `read -rp "确认? (yes/no): "` 二次确认

## pitfall

1. **标签名不要包含中文** — 中文字符在 sed/tr 中跨环境兼容性差，改用纯 ASCII 标签名 + `git tag -m "中文描述"` 存储描述
2. **snapshots/ 下的 .db 必须被 .gitignore 排除** — 否则每次快照的数据库副本进入 Git 跟踪，导致仓库膨胀
3. **回滚前一定要备份当前状态** — 用户可能回滚错了，`rollback_before_` 标签提供反悔机会
4. **验证不可少** — 做完后跑一次 `bash snapshot.sh test` + `bash rollback.sh list` + 检查数据库备份文件确实是 SQLite 格式

## 适用场景

- 对代码 + SQLite 数据库同时做版本控制的 Web CRUD 项目
- 需要频繁变动但每次变动的状态需要可恢复的内部管理系统
- 没有 CI/CD 流水线的小团队/个人项目
