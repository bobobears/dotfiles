---
name: security-audit
description: "Linux 系统安全审计 — 只读、非破坏性。检查用户/文件/SSH/网络/服务/包/日志/内核安全，生成评分和 Word 审计报告。"
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [security, audit, linux, penetration-test, compliance, hardening]
    related_skills: [hybrid-office]
---
# Security Audit Skill（Linux 系统安全审计）

## 概述

对 Linux 系统进行**只读、非破坏性**的安全审计。检查 8 大安全领域，生成安全评分（0-100）和详细发现列表，可选输出 Word 格式的审计报告。

**核心安全原则**：本工具绝不会修改系统文件、配置或服务。所有操作都是只读的。

## 触发条件

- 用户要求进行"安全审计"、"安全检查"、"安全扫描"
- 用户问"系统安全吗？"或"检查一下安全"
- 需要对系统进行合规审计或安全评估
- 需要生成安全审计报告
- **用户要求审查某个 Hermes 技能的安全性**
- **用户问"这个技能安全吗？"/"审计一下这个技能"**

## 前置条件

```bash
pip install python-docx openpyxl   # Word 报告功能需要
```

## 核心脚本

| 脚本 | 功能 |
|------|------|
| `scripts/audit.py` | Linux 系统安全审计引擎（JSON/Word 输出） |
| `scripts/audit_skills.py` | Hermes 技能安全审计引擎 |

## 审计覆盖范围

### 系统安全审计（`audit.py`）

| 分类 | 检查项 | 严重级别上限 |
|------|--------|-------------|
| `user` | 多 UID 0 用户、无密码用户、交互式账户 | HIGH |
| `sudo` | NOPASSWD 条目、额外 sudo 规则 | MEDIUM |
| `file` | 敏感文件权限、SUID/SGID 二进制、世界可写文件 | HIGH |
| `ssh` | Root登录、密码认证、密钥认证、X11转发、MaxAuthTries | HIGH |
| `network` | 开放端口、公共监听、防火墙状态、IP转发 | HIGH |
| `service` | 运行/失败服务、cron 任务 | MEDIUM |
| `package` | 可用更新、held 包、unattended-upgrades | HIGH |
| `log` | rsyslog/auditd 状态、日志文件大小 | HIGH |
| `kernel` | ASLR、SYN cookies、源路由、SELinux/AppArmor | HIGH |

### Hermes 技能安全审计（`audit_skills.py`）

审查任意 Hermes 技能的脚本、文档和参考文件中的安全风险，包括：

| 类别 | 检查项 |
|------|--------|
| 🔴 HIGH | `shell=True` 注入、`os.system()`、`eval()/exec()`、硬编码密钥、`rm -rf /` |
| 🟡 MEDIUM | 网络请求到外部 URL、文件写入/删除、sudo 使用、service 管理、包安装 |
| 🟢 LOW | TODO/FIXME 注释、临时文件、环境变量、用户输入未验证 |
| 📄 文档 | 文档中的凭证泄露、破坏性指令、缺少安全章节 |

## 快速使用

### 系统审计

```bash
# 完整安全审计
python ~/.hermes/skills/security/security-audit/scripts/audit.py

# 仅审计 SSH 和网络安全
python ~/.hermes/skills/security/security-audit/scripts/audit.py --category ssh network

# 输出 JSON + Word 报告
python ~/.hermes/skills/security/security-audit/scripts/audit.py \
  --output /tmp/audit-result.json --report-doc /tmp/audit-report.docx

# 需要 sudo 权限的检查（推荐）
python ~/.hermes/skills/security/security-audit/scripts/audit.py --sudo
```

### Hermes 技能审计

```bash
# 审计单个技能
python ~/.hermes/skills/security/security-audit/scripts/audit_skills.py hybrid-office

# 审计所有技能
python ~/.hermes/skills/security/security-audit/scripts/audit_skills.py --all

# 审计并输出 Word 报告
python ~/.hermes/skills/security/security-audit/scripts/audit_skills.py hybrid-office \
  --output /tmp/skill-audit.json --report-doc /tmp/skill-audit.docx
```

## 使用场景

### 场景 1：快速安全检查

```bash
python ~/.hermes/skills/security/security-audit/scripts/audit.py --text
```

输出示例：
```
Security Audit Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Host: my-server
OS:   Linux 6.17.0-1014-nvidia
Time: 2026-06-23T12:00:00

Security Score: 85/100
Total Findings: 12

  🔴 HIGH: 2
  🟡 MEDIUM: 5
  🟢 LOW: 3
  ℹ️ INFO: 2
```

### 场景 2：生成 Word 审计报告

结合 `hybrid-office` 技能，输出专业排版的安全审计报告：

```bash
python ~/.hermes/skills/security/security-audit/scripts/audit.py \
  --category all --output /tmp/audit.json --report-doc /tmp/security-audit.docx

# 验证报告内容
python -m markitdown /tmp/security-audit.docx | head -50
```

### 场景 3：从 JSON 结果创建自定义报告

将 JSON 结果输入 `hybrid-office` 的 Word 创建流程：

```bash
python ~/.hermes/skills/security/security-audit/scripts/audit.py \
  --output /tmp/audit.json
```

然后读取 JSON 结果，提取关键发现，用 `hybrid-office` 技能生成报告。

### 场景 4：单独审计某个领域

```bash
python ~/.hermes/skills/security/security-audit/scripts/audit.py -c ssh kernel
```

## 结果解读

### 安全评分

| 分数范围 | 评级 | 含义 |
|---------|------|------|
| 80-100 | 🟢 良好 | 安全态势良好，少量建议改进 |
| 50-79 | 🟡 一般 | 存在需要关注的中等风险 |
| 0-49 | 🔴 较差 | 存在严重安全隐患，需立即处理 |

### 严重级别

- **🔴 HIGH**: 直接安全风险（无防火墙、root SSH 登录、无密码用户）
- **🟡 MEDIUM**: 潜在风险（IP转发、无 auditd、NOPASSWD sudo）
- **🟢 LOW**: 建议改进（X11转发、日志文件过大）
- **ℹ️ INFO**: 参考信息（运行服务列表、开放端口）

## 常见错误与处理

1. **"command not found"**
   - 某些系统可能缺少 `ss`, `ufw`, `systemctl` 等工具
   - 工具缺失时该检查项会跳过，不影响其他检查

2. **Permission denied 读取 /etc/shadow**
   - 需要 root 权限。使用 `--sudo` 参数，或人工确认审计脚本的只读性质后提权

3. **Word 报告生成失败**
   ```bash
   pip install python-docx
   ```

4. **审计结果过多**
   - 先用 `--category` 指定单个分类检查，缩小范围

## 验证检查清单

- [ ] `python audit.py` 正常运行并输出结果
- [ ] 审计结果包含所有 8 个分类（指定全部时）
- [ ] 安全评分在合理范围内
- [ ] HIGH / MEDIUM 发现均有分析和建议
- [ ] Word 报告生成成功，内容完整
- [ ] 确认工具未修改任何系统文件或配置

## 安全承诺

本审计工具严格遵守：
1. **只读操作**：绝不 write/delete/chmod/service change
2. **无 shell 注入**：所有命令 `shell=False`
3. **路径白名单**：仅读取 `ALLOWED_AUDIT_PATHS` 中的配置文件
4. **超时保护**：每条命令最多跑 15 秒
5. **错误隔离**：单条命令失败不影响其他检查
