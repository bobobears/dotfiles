# xrdp-chansrv FUSE 行为记录

## 平台

- DGX Spark / Ubuntu 24.04
- xrdp 通道映射（Windows E 盘 → `~/thinclient_drives/E:/`）
- 底层：FUSE (fuse.chansrv)

## 已知异常

### 1. 符号链接不可用

```
rsync: symlink "path" -> "target" failed: Function not implemented (38)
```

**原因**：xrdp-chansrv 的 FUSE 实现不支持创建或读取符号链接。
**修复**：rsync 必须加 `--copy-links` 将符号链展开为实际文件。

### 2. 递归操作性能差

`du -sh` / `df -h` 在 fuse 盘上执行会**挂起**（不超时、不报错、一直等）。

**原因**：xrdp FUSE 对递归 inode 扫描支持有限。
**修复**：
- 用 `ls | wc -l` 替代 `du -sh` 做快速统计
- 用 `df` 无法获取可用空间，信任 Windows 端容量足够（数据只有 ~1.2GB）

### 3. 深层 mkdir -p 不稳定

一次性 `mkdir -p a/b/c/d` 可能部分失败。

**修复**：每一层目录用单独 `mkdir -p`，在 rsync 前创建好。

### 4. 不含 -J 时时间戳同步失败

```
rsync: failed to set times on "file": Function not implemented (38)
```

**修复**：加 `-J`（`--omit-dir-times`，`--omit-link-times`）。

## rsync 推荐参数

```bash
rsync -ah --delete --copy-links -J <src> <dst> \
  --exclude="__pycache__" --exclude="*.pyc" --exclude=".git" \
  --exclude="node_modules" --exclude=".venv" --exclude="venv" \
  --exclude=".mypy_cache" --exclude=".pytest_cache"
```

## 连通性检测

```bash
# 在 RDP 连接断开时，fuse 挂载点目录仍然存在但不可写
# 所以不要只检查 -d，要实际写一个文件
test_file="$BACKUP_BASE/.connectivity_test"
echo "$$" > "$test_file" 2>/dev/null || exit 1
```
