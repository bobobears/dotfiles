# 员工离职/删除后关联模块同步

## 场景

在 HRMS 类系统中，员工离职（标记 status='离职'）或物理删除后，已存在的关联数据（工资表、合同、考勤等）不会自动更新。用户反馈「删除了员工档案但工资表中还有她的条目」。

## 问题分析

| 操作 | 影响范围 | 未同步的后果 |
|------|----------|-------------|
| 物理删除（DELETE FROM employees） | 员工表记录消失，工资表 `employee_id` 变为孤立引用 | 工资明细行名前显示为空或报错 |
| 标记离职（UPDATE status='离职'） | 员工记录仍在，但新建工资表自动过滤 | 已有工资表仍包含该员工的明细行 |
| 标记离职后重新入职 | 需恢复 status='在职' | 新建工资表重新包含该员工 |

## 数据流向

```
employees (在职状态)
  └─→ salary_standards (薪资标准)
  └─→ salary_sheets → salary_details (工资表 + 明细，每月快照)
  └─→ attendance_records (考勤，按月)
  └─→ contracts (合同)
```

- **工资表明细**是创建时从标准"拍照复制"，属于**历史快照**
- **考勤记录**按月存储，属于**独立记录**
- 员工离职后，已存在的快照不会自动更新

## 处理流程

### 第一步：确认员工状态

```sql
-- 查员工是否真的被删除/离职了
SELECT id, employee_id, name, status, resign_date FROM employees WHERE name='严泱';
```

可能的结果：
- `status='在职'` — 员工仍在职，工资表中有记录是正常的
- `status='离职'` — 已标记离职，工资表需要同步
- 记录不存在 — 已被物理 DELETE

### 第二步：确认工资表哪些包含该员工

```python
# salary_details.employee_id 存的是 employees.employee_id（字符串编码）
# 注意 salary_details 的 employee_id 是 TEXT 类型
cur = await db.execute(
    "SELECT sd.id, sd.sheet_id, ss.year, ss.month "
    "FROM salary_details sd "
    "JOIN salary_sheets ss ON sd.sheet_id = ss.id "
    "WHERE sd.employee_id = ?", (emp_code,)
)
```

**⚠️ 字段类型陷阱**：`salary_details.employee_id` 是 `TEXT` 类型，存的是员工编码（如 `'0020'`），不是 `employees.id` 的整数值。查询时用字符串而非整数。

### 第三步：清除工资表明细 + 重新统计

```python
# 1. 删除指定员工在指定工资表中的明细
await db.execute(
    "DELETE FROM salary_details WHERE employee_id=? AND sheet_id IN (?, ?)",
    (emp_code, sheet_id_23, sheet_id_24)
)
await db.commit()

# 2. 重新统计每个工资表
for sid in sheet_ids:
    cur = await db.execute('''
        SELECT COUNT(*), COALESCE(SUM(total_gross),0),
               COALESCE(SUM(total_deduct),0), COALESCE(SUM(total_net),0)
        FROM salary_details WHERE sheet_id=?
    ''', (sid,))
    stats = await cur.fetchone()
    await db.execute('''
        UPDATE salary_sheets
        SET employee_count=?, total_gross=?, total_deduct=?, total_net=?
        WHERE id=?
    ''', (stats[0], round(stats[1],2), round(stats[2],2), round(stats[3],2), sid))
```

### 第四步：自动过滤（新建工资表时）

创建工资表的 SQL 已有过滤条件：

```sql
WHERE e.status != '离职'
  AND (e.hire_date IS NULL OR e.hire_date <= ?)
```

这保证离职员工不会出现在新工资表中。**已存在的工资表不受此过滤影响。**

## 权限考虑

| 操作 | 所需角色 |
|------|---------|
| 标记员工离职 | `hr` 权限 + admin/editor |
| 从工资表清除明细 | `salary` 权限 + admin/editor |
| 重新统计工资表 | `salary` 权限 + admin/editor |

## 验证

```python
# 删除/离职后验证
assert "严泱" not in httpx.get("/salary/24").text, "工资表仍有离职员工"
assert httpx.get("/salary").text.count("人") == 27  # 6月应为27人而非28人
```

## 相关陷阱

1. **employees 表主键是 `id` 不是 `employee_id`** — 但 `salary_details` 存的是 `employee_id`（字符串编码，如 `'0020'`），不是 `id`（整数值）
2. **employees.status 是中文** — `'在职'` / `'离职'`，不是布尔值 `active=1`
3. **物理 DELETE 不可逆** — 员工管理首页 `onclick=deleteEmployee(e.employee_id, '{{ e.name }}')` 调用的是 `DELETE /api/employees/{employee_id}`，会彻底删除员工记录。之后工资表中的 `employee_id` 将无法关联到员工信息
4. **标记离职（推荐）** — 使用 `status='离职'` + `resign_date` + `resign_reason` 而非物理删除。前端应在员工管理页面提供「离职」操作而非「删除」
