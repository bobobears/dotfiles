# Linux 安全审计清单

## 审计分类

### 1. 用户与账户安全 (user / sudo)
- [ ] 是否存在多个 UID 0（root 权限）用户？
- [ ] 是否存在无密码用户？
- [ ] 是否存在未使用的交互式账户？
- [ ] sudoers 是否有 NOPASSWD 条目？
- [ ] 检查 /etc/sudoers.d/ 中的规则

### 2. 文件与权限安全 (file)
- [ ] 关键系统文件权限是否正确？
  - /etc/shadow (640), /etc/passwd (644), /etc/sudoers (440)
  - /etc/ssh/sshd_config (600)
- [ ] 是否有异常 SUID/SGID 二进制文件？
- [ ] /tmp 是否有过多世界可写文件？

### 3. SSH 安全 (ssh)
- [ ] 是否允许 root SSH 登录？
- [ ] 是否启用了密码认证？
- [ ] 公钥认证是否开启？
- [ ] MaxAuthTries 是否 ≤ 3？
- [ ] X11Forwarding 是否关闭？

### 4. 网络安全 (network)
- [ ] 哪些端口在监听？
- [ ] 是否有服务绑定到 0.0.0.0（所有接口）？
- [ ] 防火墙（UFW/iptables）是否启用？
- [ ] IP 转发是否关闭？

### 5. 服务安全 (service)
- [ ] 运行了哪些服务？
- [ ] 是否有 failed 状态的服务？
- [ ] 检查系统 cron 任务
- [ ] 检查用户 cron 任务

### 6. 包管理与更新 (package)
- [ ] 系统是否为最新？
- [ ] 是否有 held（锁定）的包？
- [ ] unattended-upgrades 是否安装？

### 7. 日志与监控 (log)
- [ ] rsyslog 是否运行？
- [ ] auditd 是否运行？
- [ ] 日志文件是否过大？

### 8. 内核与系统加固 (kernel)
- [ ] SELinux / AppArmor 状态
- [ ] ASLR 是否启用？
- [ ] TCP SYN cookies 是否启用？
- [ ] Source routing 是否关闭？
- [ ] ICMP 广播忽略

## 严重级别定义

| 级别 | 含义 | 处理建议 |
|------|------|----------|
| 🔴 HIGH | 直接安全风险 | 立即修复 |
| 🟡 MEDIUM | 潜在风险 | 安排修复 |
| 🟢 LOW | 建议改进 | 酌情处理 |
| ℹ️ INFO | 信息参考 | 无需处理 |

## 安全评分体系

- 满分 100
- HIGH 每个扣 15 分
- MEDIUM 每个扣 5 分
- LOW 每个扣 2 分
- INFO / ERROR 不扣分
