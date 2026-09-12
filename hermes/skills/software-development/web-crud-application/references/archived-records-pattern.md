# 归档记录模式 — 实现参考

## 完整代码示例（HRMS 离职人员功能）

以下代码来自人力资源管理系统的「离职人员」功能，可直接作为模板复用到其他业务系统。

### 后端路由

```python
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页：过滤离职人员 + 传递统计数据"""
    user = await require_login(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, employee_id, name, department, position, status, phone "
            "FROM employees WHERE status != '离职' ORDER BY updated_at DESC"
        )
        employees = await cursor.fetchall()
        total_all = (await db.execute_fetchall("SELECT COUNT(*) as c FROM employees"))[0][0]
        total_inactive = (await db.execute_fetchall(
            "SELECT COUNT(*) as c FROM employees WHERE status='离职'"
        ))[0][0]
    return HTMLResponse(render(
        "index.html", request=request, employees=[dict(e) for e in employees],
        current_user=user, total_all=total_all, total_inactive=total_inactive,
    ))


@app.get("/archived", response_class=HTMLResponse)
async def archived_list(request: Request):
    """离职人员列表"""
    user = await require_login(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    if user["role"] not in ("admin", "editor"):
        raise HTTPException(403, "权限不足")

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, employee_id, name, department, position, status, phone, resign_date, resign_reason "
            "FROM employees WHERE status='离职' ORDER BY resign_date DESC, updated_at DESC"
        )
        employees = await cursor.fetchall()
    return HTMLResponse(render(
        "archived.html", request=request, employees=[dict(e) for e in employees],
        current_user=user,
    ))
```

### 首页模板 — 统计卡片（可点击跳转）

```html
<div class="stats">
    <!-- 员工总数（含离职） -->
    <div class="stat-card">
        <div class="num">{{ total_all }}</div>
        <div class="label">员工总数</div>
    </div>
    <!-- 在职人数 -->
    <div class="stat-card">
        <div class="num">{{ active }}</div>
        <div class="label">在职人数</div>
    </div>
    <!-- 其他（退休等） -->
    <div class="stat-card">
        <div class="num">{{ total_all - active - total_inactive }}</div>
        <div class="label">其他</div>
    </div>
    <!-- 离职人数 → 可点击跳转（仅admin/editor可见） -->
    {% if current_user.role in ('admin', 'editor') %}
    <div class="stat-card" style="cursor:pointer;" onclick="location.href='/archived'">
        <div class="num" style="color:var(--text-secondary);">{{ total_inactive }}</div>
        <div class="label" style="color:var(--primary);text-decoration:underline;">离职人员 →</div>
    </div>
    {% endif %}
</div>
```

### archived.html 模板

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>离职人员 — HRMS</title>
    <style>
        /* 复用首页的 CSS 变量和基础样式 */
        :root {
            --primary: #2563eb;
            --bg: #f8fafc;
            --card: #ffffff;
            --border: #e2e8f0;
            --text: #1e293b;
            --text-secondary: #64748b;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC", sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header {
            background: var(--card);
            border-bottom: 1px solid var(--border);
            padding: 16px 0;
            margin-bottom: 24px;
        }
        .header-inner {
            max-width: 1200px; margin: 0 auto; padding: 0 20px;
            display: flex; justify-content: space-between; align-items: center;
        }
        .header h1 { font-size: 20px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
        .header h1 small { font-size: 13px; font-weight: 400; color: var(--text-secondary); margin-left: 8px; }
        .btn { /* 与首页一致 */ }
        .btn-outline { /* 与首页一致 */ }
        .btn-sm { padding: 4px 10px; font-size: 13px; }
        .search-bar { /* 与首页一致 */ }
        .table-wrap { /* 与首页一致 */ }
        table { /* 与首页一致 */ }
        th, td { padding: 10px 14px; text-align: left; font-size: 14px; }
        th { background: var(--bg); font-weight: 600; color: var(--text-secondary); font-size: 13px; }
        td { border-bottom: 1px solid var(--border); }
        tr:hover { background: #f1f5f9; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 500; }
        .badge-inactive { background: #fef2f2; color: #991b1b; }
        .empty { text-align: center; padding: 60px 20px; color: var(--text-secondary); }
        .empty .icon { font-size: 48px; margin-bottom: 16px; opacity: 0.4; }
        .actions { display: flex; gap: 6px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-inner">
            <h1>
                📋 离职人员
                <small>{{ employees|length }} 人</small>
            </h1>
            <div style="display:flex;align-items:center;gap:12px;">
                <span style="font-size:13px;color:var(--text-secondary);">
                    👤 {{ current_user.display_name }}
                </span>
                <a href="/" class="btn btn-outline btn-sm">← 返回首页</a>
                <a href="/logout" class="btn btn-outline" style="font-size:13px;">退出</a>
            </div>
        </div>
    </div>

    <div class="container">
        <div class="search-bar">
            <input type="text" id="searchInput" placeholder="搜索姓名、工号、部门…" oninput="filterTable()">
        </div>

        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>工号</th>
                        <th>姓名</th>
                        <th>部门</th>
                        <th>岗位</th>
                        <th>电话</th>
                        <th>状态</th>
                        <th>离职日期</th>
                        <th>离职原因</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody id="employeeTable">
                    {% for emp in employees %}
                    <tr>
                        <td><strong>{{ emp.employee_id }}</strong></td>
                        <td><a href="/view/{{ emp.employee_id }}" style="color:var(--primary);text-decoration:none;">{{ emp.name }}</a></td>
                        <td>{{ emp.department }}</td>
                        <td>{{ emp.position }}</td>
                        <td>{{ emp.phone }}</td>
                        <td><span class="badge badge-inactive">离职</span></td>
                        <td>{{ emp.resign_date or '-' }}</td>
                        <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ emp.resign_reason or '-' }}</td>
                        <td><a href="/view/{{ emp.employee_id }}" class="btn btn-outline btn-sm">查看</a></td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="9">
                            <div class="empty">
                                <div class="icon">📭</div>
                                <p>暂无离职人员记录</p>
                            </div>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function filterTable() {
            const q = document.getElementById('searchInput').value.toLowerCase();
            document.querySelectorAll('#employeeTable tr').forEach(row => {
                row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
            });
        }
    </script>
</body>
</html>
```

### 归档操作 API（标记离职）

```python
@app.post("/api/employees/{employee_id}/archive")
async def archive_employee(request: Request, employee_id: str):
    user = await require_login(request)
    if user["role"] not in ("admin", "editor"):
        raise HTTPException(403, "权限不足")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(str(DB_PATH)) as db:
        cursor = await db.execute(
            "UPDATE employees SET status='离职', resign_date=?, updated_at=? WHERE employee_id=?",
            (now[:10], now, employee_id),
        )
        await db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(404, "员工不存在")
    return {"ok": True}
```

## 关键设计决策

1. **SQL 级过滤 vs 前端 JS 过滤**：使用后端 SQL `WHERE status != '离职'` 而非前端隐藏行，因为：
   - 前端过滤可被用户绕过（开发者工具修改 JS）
   - 统计数字需要基于正确子集
   - 大数据量下前端渲染所有记录会变慢
2. **独立路由 vs 查询参数**：使用独立页面 `/archived` 而非 `/employees?status=离职`，因为：
   - 页面布局和列数不同（多了离职日期/原因）
   - URL 语义清晰，方便分享
   - 权限可以单独控制（viewer 看不到归档页）
3. **统计卡片传递 `total_all` 和 `total_inactive` 而非从模板计算**：因为首页只加载非离职员工列表，无法在 Jinja2 中计算离职人数，需要后端单独 COUNT 查询。
