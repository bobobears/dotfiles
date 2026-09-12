# 薪资标准 vs 工资表明细的同步机制

## 设计模式：单向复制（时点冻结）

薪酬模块中，`salary_standards`（薪资标准）和 `salary_sheets → salary_details`（工资表）是独立的三张表。标准→明细是**单向一次性复制**：

```
salary_standards                  salary_details
  ├─ base_salary  ← 随时可改          ├─ base_salary  ← 创建时复制，冻结
  ├─ allow_admin  ← 随时可改          ├─ allow_admin  ← 创建时复制，冻结
  ├─ social_base  ← 随时可改          ├─ deduct_social ← 创建时按 base×rate 算出
  └─ ...                             └─ ...
         │
         ▼ (新建工资表时一次性复制)
    salary_details                   ← 标准修改后不会自动更新
```

### 设计原因

- **时点冻结**：工资表代表某个月的实际核算，不因标准变动而追溯修改
- **历史稳定**：confirmed/paid 状态的工资表不可改
- **用户常见困惑**："我改了行政补助/基本工资，但工资表没变"——这是预期行为，不是 bug

### 用户常见反应 & 对应回复

| 用户说 | 应回复 |
|--------|--------|
| "我改了补助/基本工资，但工资表没变" | 解释时点冻结，提供"从标准同步"按钮 |
| "新建工资表能用新值吗？" | "可以，新建时自动取最新标准" |
| "已发放的能改吗？" | "不可。需新建下个月的工资表" |

### 热同步（draft 状态可用）

**条件**：工资表状态必须为 draft。前端"从标准同步"按钮，后端 `POST /api/salary/sheets/{id}/sync-standard`。

**同步的内容**：base_salary, allow_*（7项）, deduct_social, deduct_housing ← 从标准重新计算

**不同步的内容**（现场编辑数据，保持独立）：
- 考勤（attend_*）— 每月不同
- 绩效（perf_*）— 每月不同
- other 扣款 JSON — 每月不同

同步后自动重算 total_gross/total_deduct/total_net。

### 后端实现要点

```python
@app.post("/api/salary/sheets/{sheet_id}/sync-standard"):
    1. 检查 sheet.status == 'draft'
    2. 从 salary_details 获取所有 employee_id
    3. 批量查询 salary_standards WHERE employee_id IN (...)
    4. 逐条 UPDATE salary_details（base_salary, allow_*, deduct_social, deduct_housing）
    5. 每条重新计算 total_gross/total_deduct/total_net
    6. commit → return {"ok": True, "updated": N}
```

### 验证方法

```bash
# 1. 改标准
sqlite3 db/hrms.db "UPDATE salary_standards SET allow_admin=1000 WHERE employee_id='002'"

# 2. 调同步 API（需已登录获取 cookie）
curl -X POST -b cookies.txt localhost:8000/api/salary/sheets/14/sync-standard

# 3. 验证明细更新
sqlite3 db/hrms.db "SELECT d.employee_id, e.name, d.allow_admin FROM salary_details d JOIN employees e ON d.employee_id=e.employee_id WHERE d.sheet_id=14"
```
