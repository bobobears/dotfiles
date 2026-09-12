# 四项补助自动等级化计算（实现参考）

## 核心数据模型

`salary_basics` 表在原有结构上加 `grade TEXT` 字段后，用统一的 category+grade+item_value 模式存储所有补助等级。

### 等级配置种子数据

```sql
-- 行政补助
INSERT INTO salary_basics (category, grade, item_name, item_value, unit, description)
VALUES
('allowance_level_admin', '',       '一般人员行政补助', 100.0, '元', '适用于无行政级别或None'),
('allowance_level_admin', '主办',   '主办行政补助',     200.0, '元', '适用于行政级别=主办'),
('allowance_level_admin', '主管',   '主管行政补助',     400.0, '元', '适用于行政级别=主管'),
('allowance_level_admin', '副职',   '副职行政补助',     600.0, '元', '适用于行政级别=副职'),
('allowance_level_admin', '正职',   '正职行政补助',     800.0, '元', '适用于行政级别=正职');

-- 岗位补助
INSERT INTO salary_basics (category, grade, item_name, item_value, unit, description)
VALUES
('allowance_level_position', 'doctor',     '医生岗位补助',     500.0, '元', '适用于技术职务含医生'),
('allowance_level_position', 'non_doctor', '非医生岗位补助',   200.0, '元', '适用于技术职务不含医生');

-- 技能补助
INSERT INTO salary_basics (category, grade, item_name, item_value, unit, description)
VALUES
('allowance_level_skill', '',       '其他技能补助',    0.0,   '元', '其他未分类职称'),
('allowance_level_skill', '无',     '无职称技能补助',  0.0,   '元', '职称=无'),
('allowance_level_skill', '初级',   '初级技能补助',    200.0, '元', '职称=初级'),
('allowance_level_skill', '中级',   '中级技能补助',    400.0, '元', '职称=中级'),
('allowance_level_skill', '副高',   '副高技能补助',    600.0, '元', '职称=副高'),
('allowance_level_skill', '高级',   '高级技能补助',    800.0, '元', '职称=高级');

-- 工龄补助（每5年一级）
INSERT INTO salary_basics (category, grade, item_name, item_value, unit, description)
VALUES
('allowance_level_seniority', '0-4',   '工龄0-4年补助',    0.0,   '元', '入职不满5年'),
('allowance_level_seniority', '5-9',   '工龄5-9年补助',  100.0,  '元', '入职满5年不满10年'),
('allowance_level_seniority', '10-14', '工龄10-14年补助', 200.0,  '元', '入职满10年不满15年'),
('allowance_level_seniority', '15-19', '工龄15-19年补助', 300.0,  '元', '入职满15年不满20年'),
('allowance_level_seniority', '20-24', '工龄20-24年补助', 400.0,  '元', '入职满20年不满25年'),
('allowance_level_seniority', '25-29', '工龄25-29年补助', 500.0,  '元', '入职满25年不满30年'),
('allowance_level_seniority', '30+',   '工龄30年及以上',   600.0,  '元', '入职满30年');
```

## 后端核心代码

### 1. 加载等级数据

```python
async def _load_allowance_levels(db) -> dict:
    cur = await db.execute(
        "SELECT category, grade, item_value, item_name FROM salary_basics "
        "WHERE category LIKE 'allowance_level_%' ORDER BY category"
    )
    rows = await cur.fetchall()
    levels = {}
    for r in rows:
        cat = r["category"]
        if cat not in levels:
            levels[cat] = {}
        levels[cat][r["grade"]] = r["item_value"]
    return levels
```

### 2. 计算四项补助

```python
async def calc_employee_allowances(employee_id: str, db) -> dict:
    cur = await db.execute(
        "SELECT admin_level, tech_position, qualification, hire_date "
        "FROM employees WHERE employee_id=?", (employee_id,)
    )
    emp = await cur.fetchone()
    if not emp:
        return {"allow_admin": 0, "allow_position": 0,
                "allow_skill": 0, "allow_seniority": 0}

    levels = await _load_allowance_levels(db)
    admin_levels = levels.get("allowance_level_admin", {})
    position_levels = levels.get("allowance_level_position", {})
    skill_levels = levels.get("allowance_level_skill", {})
    seniority_levels = levels.get("allowance_level_seniority", {})

    # 行政补助
    al = (emp["admin_level"] or "").strip()
    admin_val = admin_levels.get(al, 0) or 0
    if admin_val == 0:
        admin_val = admin_levels.get("", 0) or 0

    # 岗位补助
    tp = (emp["tech_position"] or "")
    if tp and "医生" in tp:
        pos_val = position_levels.get("doctor", 0) or 0
    else:
        pos_val = position_levels.get("non_doctor", 0) or 0

    # 技能补助
    q = (emp["qualification"] or "").strip()
    skill_val = skill_levels.get(q, 0) or 0
    if skill_val == 0:
        skill_val = skill_levels.get("", 0) or 0

    # 工龄补助
    hired = (emp["hire_date"] or "")[:10]
    years = 0
    if hired:
        from datetime import date
        parts = hired.split("-")
        hire_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
        today = date.today()
        years = today.year - hire_date.year
        if (today.month, today.day) < (hire_date.month, hire_date.day):
            years -= 1
        years = max(0, years)

    sen_val = 0
    for grade_range, val in sorted(seniority_levels.items(),
                                    key=lambda x: (x[0] != "30+", x[0])):
        if grade_range == "30+":
            if years >= 30:
                sen_val = val or 0
                break
        else:
            parts = grade_range.split("-")
            lo, hi = int(parts[0]), int(parts[1])
            if lo <= years <= hi:
                sen_val = val or 0
                break

    return {
        "allow_admin": admin_val,
        "allow_position": pos_val,
        "allow_skill": skill_val,
        "allow_seniority": sen_val,
    }
```

### 3. API 路由

```python
@app.get("/api/salary/standards/calc/{employee_id}")
async def api_calc_allowances(request: Request, employee_id: str):
    user = await require_permission(request, "salary")
    if user is None:
        raise HTTPException(401, "未登录")
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        allowances = await calc_employee_allowances(employee_id, db)
    return allowances
```

### 4. POST/PUT 纯自动模式（2026-07-20 最终确认）

> **设计变更**：初始版本允许手动覆盖（传值非0保留），用户要求改为纯自动，已应用。

```python
# POST 新建
auto = await calc_employee_allowances(data.employee_id, db)
# 纯自动：全部用服务端计算的覆盖
allow_admin = auto["allow_admin"]
allow_position = auto["allow_position"]
allow_skill = auto["allow_skill"]
allow_seniority = auto["allow_seniority"]

# PUT 编辑——同样忽略前端传入值
auto = await calc_employee_allowances(employee_id, db)
```

### 5. calc-all 批量重新计算
```python
@app.post("/api/salary/standards/calc-all")
async def api_calc_all(request: Request):
    # 遍历所有薪资标准，重新计算四项补助并更新
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT id, employee_id FROM salary_standards")
        rows = await cur.fetchall()
        updated = 0
        for r in rows:
            auto = await calc_employee_allowances(r["employee_id"], db)
            await db.execute("""
                UPDATE salary_standards SET
                    allow_admin=?, allow_position=?,
                    allow_skill=?, allow_seniority=?, updated_at=datetime('now')
                WHERE id=?
            """, (auto["allow_admin"], auto["allow_position"],
                  auto["allow_skill"], auto["allow_seniority"], r["id"]))
            updated += 1
        await db.commit()
    return {"ok": True, "updated": updated}
```

## 前端代码（纯自动模式）

### 模态框中的只读显示
薪资标准新增/编辑模态框中，四项补助用 `<span>` 替代 `<input>`，显示自动计算值：

```html
<div class="form-group">
    <label>行政补助 <span class="auto-badge">(自动)</span></label>
    <span id="allowAdmin" class="auto-value">0</span>
</div>
```

### 工龄显示（员工编辑页）
```javascript
function calcSeniority() {
    const hireDate = document.getElementById('hire_date').value;
    const display = document.getElementById('seniority_display');
    if (!hireDate) { display.textContent = ''; return; }
    const hired = new Date(hireDate);
    const now = new Date();
    let years = now.getFullYear() - hired.getFullYear();
    const mDiff = now.getMonth() - hired.getMonth();
    if (mDiff < 0 || (mDiff === 0 && now.getDate() < hired.getDate())) years--;
    years = Math.max(0, years);
    display.textContent = years === 0 ? '（工龄不满1年）' : `（工龄 ${years} 年）`;
}
```

### 批量管理页面
`/admin/batch-allowances` 表格中每个员工一行，包含：
- 行政级别下拉（正职/副职/主管/主办/一般人员）
- 技术职务下拉（医生/护士/实习医生/化验员/药剂士等）
- 职称下拉（高级/副高/主治医师/中级/初级/无）
- 工龄（只读，由 hire_date 自动计算显示）
- save 按钮 → 保存员工档案字段 → 自动调用 calc-all 批量刷新薪资标准

## 注意点

1. **`_load_allowance_levels()` 必须在每个 `async with db` 连接块内部调用**，因为 aiosqlite 连接不能跨协程传递
2. **等级匹配顺序**：工龄等级遍历前先按 `(is_30plus, grade_string)` 排序确保 `30+` 在最后检查
3. **纯自动模式**：前端不提供输入框，所有修改通过批量管理页面调整员工档案字段实现
4. **岗位补助的关键词判断**：`"医生" in tech_position` 包含"医生"、"实习医生"、"主治医生"，但不含"化验员"、"药剂士"、"护士"
5. **技能补助的空值 fallback**：`qualification` 为 NULL 或空字符串时，先查 `grade=''` 的条目
6. **calc-all 端点**：员工档案变更（行政级别/技术职务/职称/工龄）后，需调用此端点刷新薪资标准
