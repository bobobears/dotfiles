# 安全审计使用指南

## 快速命令

```bash
# 完整审计（文本输出）
python ~/.hermes/skills/security/security-audit/scripts/audit.py

# 指定分类审计
python ~/.hermes/skills/security/security-audit/scripts/audit.py --category ssh network

# 输出 JSON 结果
python ~/.hermes/skills/security/security-audit/scripts/audit.py --output /tmp/audit.json

# 输出 JSON + Word 报告
python ~/.hermes/skills/security/security-audit/scripts/audit.py \
  --output /tmp/audit.json --report-doc /tmp/audit-report.docx

# 需要 sudo 权限的检查
python ~/.hermes/skills/security/security-audit/scripts/audit.py --sudo
```

## JSON 输出结构

```json
{
  "audit_time": "2026-06-23T12:00:00",
  "hostname": "hostname",
  "os": "Linux 6.17.0",
  "use_sudo": false,
  "summary": {
    "total_findings": 15,
    "by_severity": {"HIGH": 2, "MEDIUM": 5, "LOW": 3, "INFO": 5},
    "score": 85
  },
  "categories_audited": ["user", "file", "ssh", "network"],
  "findings": [
    {
      "severity": "HIGH",
      "category": "network",
      "title": "UFW firewall is INACTIVE",
      "detail": "Uncomplicated Firewall is not enabled",
      "recommendation": "Enable firewall: sudo ufw enable"
    }
  ]
}
```

## 与 hybrid-office 技能配合

审计结果可直接生成规范的 Word 报告文档：

```bash
python ~/.hermes/skills/security/security-audit/scripts/audit.py \
  --category all \
  --output /tmp/audit-result.json \
  --report-doc /tmp/security-report.docx
```

## 安全设计原则

本工具严格遵守以下安全原则：

1. **只读操作** — 绝不修改任何系统文件或配置
2. **无 shell 注入** — 所有命令使用 subprocess.run 且 shell=False
3. **路径白名单** — 仅读取已知的安全配置文件
4. **无破坏性命令** — 不执行 write/delete/chmod/service change
5. **超时保护** — 所有命令有 15 秒超时
6. **错误安全** — 任何命令失败不会影响其他检查
