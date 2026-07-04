---
name: lvm-live-migration
description: "无损将单根 ext4 分区迁移为 LVM 布局：ext4 缩容 → 分区缩小 → LVM PV/VG/LV → 挂载 /home 和 /data，数据不丢失"
version: 1.0.0
author: Hermes
platforms: [linux]
metadata:
  hermes:
    tags: [lvm, partition, live-migration, ext4, ubuntu]
---

# LVM 无损迁移：单分区 → 多逻辑卷

## Overview

将现有 Ubuntu 系统的**单根 ext4 分区**（占满整盘）无损转换为 **LVM 布局**，无需重装、数据不丢失。

最终分区结构：

```
nvme0n1
├── nvme0n1p1  EFI (298M)     → /boot/efi
├── nvme0n1p2  ext4 (200G)    → /          (缩小后)
└── nvme0n1p3  LVM PV (3.5T)  → LVM 池
    ├── vg-root (200G) ext4   → /          (迁移后)
    ├── vg-home (500G) ext4   → /home
    └── vg-data (剩余) ext4   → /data
```

## Prerequisites

- Ubuntu 24.04 Live USB（用于离线操作，因为根分区不能在线缩小）
- 当前磁盘空闲 ≥ 3.3T（已确认：3.7T 盘只用 147G）
- 确保重要数据有**额外备份**（虽然操作本身不丢数据）

## 适用环境

确认以下条件匹配再执行：

```bash
# 1. GPT 分区表
sudo fdisk -l /dev/nvme0n1 | head -3   # 确认 "磁盘标签类型：gpt"

# 2. 单 ext4 根分区
lsblk -f                               # 确认 p2 是 ext4，挂载 /

# 3. 空间充足
df -h /                                # 已用 % 应在 10% 以下
```

## Workflow

### 预备：下载 Live USB

1. 下载 Ubuntu 24.04 ISO
2. 制作启动 U 盘：`sudo dd if=ubuntu-24.04-desktop-amd64.iso of=/dev/sdX bs=4M status=progress`
3. 确保有 **root 密码**（`sudo passwd root`）或 sudo 权限

### Phase 1 — 进 Live 环境

```bash
# 重启进 U 盘里的 Ubuntu Live
# 选 "Try Ubuntu"（试用），不要点安装
```

### Phase 2 — 缩容 ext4 文件系统

```bash
# 1. 找到根分区（通常 /dev/nvme0n1p2）
lsblk -f

# 2. 检查 ext4 状态
sudo e2fsck -f /dev/nvme0n1p2

# 3. 缩小文件系统到 200G（比目标分区略小）
sudo resize2fs /dev/nvme0n1p2 200G
# ⏱ 耗时约 20-40 分钟，取决于文件分布
```

> ⚠️ `resize2fs` 操作的**不是分区表**，而是 ext4 内部数据布局。**不出错就不会丢数据**。如果中途关机等极端情况，`e2fsck -f` 可修复。

### Phase 3 — 缩小分区

```bash
# 1. 查看当前分区布局
sudo fdisk -l /dev/nvme0n1

# 2. 删除并重建分区 2（只改分区表大小，数据不动！）
sudo fdisk /dev/nvme0n1

# fdisk 交互命令：
# p          ← 确认当前布局，记下 p2 的起点（Start 扇区，通常是 612352）
# d          ← 删除分区（选 2，即根分区）
# n          ← 新建分区
#   分区号: 2
#   起点:   <输入上一步记下的起点，直接回车默认即可>
#   终点:   +200G   ← 只给 200G
#   类型:   按回车默认（Linux filesystem）
# w          ← 写入并退出
```

> ⚠️ **关键**：新建 p2 时起点**必须**等于原 p2 的起点，否则数据全丢！

或使用 `parted` 替代 fdisk（更安全直观）：

```bash
sudo parted /dev/nvme0n1
(parted) unit s print            # 显示以扇区为单位
(parted) resizepart 2 419432448  # 419432448 = 612352 + 200*1024*1024*1024/512 - 1
# 或直接：resizepart 2 200GB
(parted) quit
```

### Phase 4 — 创建 LVM 物理卷和卷组

```bash
# 1. 创建新分区 p3（用剩余空间）
sudo fdisk /dev/nvme0n1
# n → 分区号 3 → 起点默认 → 终点默认（用满剩余）→ w

# 2. 创建 LVM 物理卷
sudo pvcreate /dev/nvme0n1p3

# 3. 创建 LVM 卷组
sudo vgcreate vg0 /dev/nvme0n1p3
```

### Phase 5 — 创建逻辑卷并格式化

```bash
# 1. 创建 /home 逻辑卷（500G）
sudo lvcreate -L 500G -n lv_home vg0

# 2. 创建 /data 逻辑卷（剩余全部）
sudo lvcreate -l 100%FREE -n lv_data vg0

# 3. 格式化
sudo mkfs.ext4 /dev/vg0/lv_home
sudo mkfs.ext4 /dev/vg0/lv_data
```

### Phase 6 — 迁移数据和挂载

```bash
# 1. 挂载新卷并复制 /home
sudo mount /dev/vg0/lv_home /mnt/home
sudo cp -a /home/* /mnt/home/
# ⏱ 时间取决于 /home 大小，通常几分钟

# 2. 挂载新 /data 卷
sudo mount /dev/vg0/lv_data /mnt/data

# 3. 挂载原根分区（已缩小到 200G）
sudo mount /dev/nvme0n1p2 /mnt/root
```

### Phase 7 — 更新 fstab 和 GRUB

```bash
# 1. 记录 LVM 逻辑卷的 UUID
sudo blkid /dev/vg0/lv_home
sudo blkid /dev/vg0/lv_data

# 2. chroot 进系统
sudo mount --bind /dev /mnt/root/dev
sudo mount --bind /proc /mnt/root/proc
sudo mount --bind /sys /mnt/root/sys
sudo chroot /mnt/root

# 3. 编辑 /etc/fstab，添加 /home 和 /data 条目
# 格式：
# UUID=<lv_home_uuid>  /home  ext4  defaults  0  2
# UUID=<lv_data_uuid>  /data  ext4  defaults  0  2

# 4. 安装 LVM 引导支持
apt update
apt install -y initramfs-tools lvm2
update-initramfs -u -k all

# 5. 更新 GRUB
update-grub
grub-install /dev/nvme0n1

# 6. 退出 chroot
exit
```

### Phase 8 — 重启验证

```bash
# Live 环境中卸载并重启
sudo umount -R /mnt
sudo reboot
```

重启进入正常系统后验证：

```bash
lsblk -f                              # 确认 LVM 布局
df -h                                 # 确认 /home 和 /data 挂载
mount | grep -E "(/home|/data)"       # 确认 LVM 设备
```

> 💡 如果重启后进不了系统，Live USB chroot 回去检查 `/etc/fstab` UUID 是否正确，或 `update-initramfs -u` 后再试。

## Verification

```bash
# 最终验证
sudo lvdisplay       # 所有逻辑卷状态
sudo pvdisplay       # 物理卷状态
sudo vgdisplay       # 卷组状态
df -h                # 空间使用
lsblk -f             # 完整拓扑
```

## 重装策略（未来）

### 利用 LVM 做无痛重装

布局已准备好后，**重装 Ubuntu 时不格式化 `/home` 和 `/data` 的 LVM 逻辑卷**：

1. 安装器选 **"手动分区"**（Something else）
2. 定位到 `lv_root`（或你的根逻辑卷），**格式化为 ext4**（仅格式化根）
3. 确保 `lv_home` 和 `lv_data` **不勾选"格式化"**
4. 挂载点对应设为 `/`、`/home`、`/data`
5. 安装完成后，`/home` 和 `/data` 数据完好如初

也可直接在安装器中操作 p2 分区（ext4 根），同样只格式化根分区，不碰其他卷。

## Pitfalls

- ⚠️ **分区起点必须一致** — 重建 p2 时，起点扇区必须等于原 p2 起点（612352），否则数据全丢
- ⚠️ **resize2fs 不能小于已用空间** — 我们缩到 200G，已用只有 147G，安全
- ⚠️ **Live USB 需要联网** — 可能需要在 Live 环境里 `sudo apt update` 装 lvm2
- ⚠️ **LVM 不参与引导** — 根分区 p2 仍然是 ext4（非 LVM），`/` 不用 LVM 卷，引导兼容性最好
- ⚠️ **不要在 Live 环境里挂载根分区为读写后直接修改文件** — 可能是旧状态
- ⚠️ `cp -a /home/* /mnt/home/` 会丢失隐藏文件（`.*` 开头），用 `cp -a /home/. /mnt/home/` 或 `rsync -a /home/ /mnt/home/`
- ⚠️ **如果启动失败** — 回到 Live USB → chroot → `journalctl -xb` 查看启动日志 → 检查 `/etc/fstab`
