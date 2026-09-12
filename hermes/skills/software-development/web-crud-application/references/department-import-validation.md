# 导入后 department 字段校验

从 Excel 导入员工数据后，`department` 字段可能只写了笼统的大部门名（如"行政部"），而实际行政归属在 `admin_dept`（如"主任室,党支部"）。

## 触发信号

用户说"XXX 的部门不对"、"XXX 不是 XX 部门的"

## 诊断

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('db/hrms.db')
conn.row_factory = sqlite3.Row
cur = conn.execute('SELECT name, department, admin_dept, tech_dept FROM employees')
for r in cur.fetchall():
    dept = r['department'] or ''
    admin = r['admin_dept'] or ''
    tech = r['tech_dept'] or ''
    if dept and dept not in (admin, tech):
        print(f'❌ {r[\"name\"]}: dept={dept} / admin={admin} / tech={tech}')
    elif not dept:
        print(f'⚠️  {r[\"name\"]}: department 为空')
"
```

## 修复

```sql
UPDATE employees SET department=admin_dept WHERE name='XXX';
```

## 系统性问题

如果涉及多名员工，说明导入映射逻辑有系统性错误，需在 ETL 脚本层面修复。
