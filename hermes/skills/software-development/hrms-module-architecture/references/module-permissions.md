# 模块级权限隔离方案（2026-07-20 实施）

## 架构概览

基于 `users` 表的 `permissions` 字段（JSON 字符串数组），实现 **模块级** 权限控制，独立于传统的 `role` 体系。

```
users 表
├── username   TEXT PK     -- 登录名
├── password   TEXT        -- SHA256 哈希
├── display_name TEXT
├── role       TEXT        -- admin / editor / viewer (传统的角色体系)
├── permissions TEXT       -- JSON 数组 ["salary", "hr", "attendance"]  ← 模块级权限
├── active     INTEGER     -- 启用/禁用
└── created_at TEXT

## 当前可用权限值

| 值 | 含义 | 对应路由 |
|----|------|----------|
| `salary` | 薪酬管理 | `/salary`, `/salary/standards`, `/salary/basics` |
| `hr` | 人事管理 | `/contracts`, `/employees` |
| `attendance` | 考勤管理 | `/attendance` |
```

## 后端实现

### 一、require_login — 必须在登录时存 permissions

```python
# ❌ 错误：登录时只存 username, display_name, role
_active_tokens[token] = {
    "username": row["username"],
    "display_name": row["display_name"],
    "role": row["role"],
}
# 这样 require_permission 拿到的 permissions 永远为空

# ✅ 正确：必须从 SQL 取 permissions 列并存到 session
# SQL:
"SELECT username, display_name, role, permissions, active FROM users WHERE username=? AND password=?"
# 然后：
_active_tokens[token] = {
    "username": row["username"],
    "display_name": row["display_name"],
    "role": row["role"],
    "permissions": row["permissions"],  # 这是必需的
}
```

### 二、require_permission 中间件

```python
# 装饰器/中间件核心逻辑
def require_permission(perm_name):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user = await require_login(request)
            if user is None:
                raise HTTPException(401, "未登录")
            
            # admin 免检 — 拥有所有权限
            if user["role"] == "admin":
                return await func(request, *args, **kwargs)
            
            # 解析 permissions（JSON 字符串 → list）
            perms = json.loads(user.get("permissions", "[]"))
            if perm_name not in perms:
                raise HTTPException(403, f"权限不足，需要「{perm_name}」权限")
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
```

### 三、路由标注

```python
@app.get("/salary")
@require_permission("salary")
async def salary_page(request: Request):
    ...

@app.get("/contracts")
@require_permission("hr")
async def contracts_page(request: Request):
    ...
```

### 四、admin 用户管理 API

#### 创建用户时写 permissions

```python
# POST /api/admin/users
await db.execute(
    "INSERT INTO users (username, password, display_name, role, permissions) VALUES (?, ?, ?, ?, ?)",
    (data.username, pw_hash, data.display_name or data.username, data.role, data.permissions or '[]'),
)
```

#### 更新用户时支持 permissions 字段

```python
# PUT /api/admin/users/{id}
if data.permissions is not None:
    updates["permissions"] = data.permissions
```

其中 `UserUpdate` Pydantic 模型需包含：

```python
class UserUpdate(BaseModel):
    password: Optional[str] = None
    display_name: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[str] = None   # JSON 字符串，如 '["salary","hr"]'
    active: Optional[int] = None
```

## 前端实现

### 渲染权限标签（Jinja2 模板）

后端传给模板时先解析 permissions：

```python
user_list = []
for u in users:
    d = dict(u)
    try:
        d["perms_list"] = json.loads(d.get("permissions", "[]"))
    except (json.JSONDecodeError, TypeError):
        d["perms_list"] = []
    user_list.append(d)
```

模板中直接用列表判断：

```html
<td>
    {% set perms = u.perms_list | default([]) %}
    {% if 'salary' in perms %}<span class="perm-tag perm-salary">薪酬</span>{% endif %}
    {% if 'hr' in perms %}<span class="perm-tag perm-hr">人事</span>{% endif %}
</td>
```

### 权限复选框（编辑弹窗）

**关键模式：用 HTML data 属性传 JSON，不用函数参数**

```html
<!-- ✅ 正确：data-permissions 属性 -->
<button onclick="editUser(this, ...)" data-permissions='{{ u.permissions | default("[]") }}'>编辑</button>

<!-- ❌ 错误：onclick 参数传 JSON —— Jinja2 | e 会转义双引号 -->
<button onclick="editUser(..., '{{ u.permissions | e }}')">编辑</button>  <!-- 双引号变 &quot; -->
```

JS 端从 `data-*` 属性读取：

```javascript
function editUser(self, id, username, displayName, role, active) {
    const permsAttr = self.getAttribute('data-permissions') || '[]';
    let perms;
    try { perms = JSON.parse(permsAttr); } catch(e) { perms = []; }
    // 勾选复选框
    document.getElementById('permSalary').checked = perms.includes('salary');
    document.getElementById('permHr').checked = perms.includes('hr');
    document.getElementById('permAttendance').checked = perms.includes('attendance');
}
```

### 权限复选框 HTML 模板

```html
<div class="form-group">
    <label>模块权限（可选，仅 editor/viewer 生效）</label>
    <div class="checkbox-group">
        <label><input type="checkbox" id="permSalary" value="salary"> 薪酬管理</label>
        <label><input type="checkbox" id="permHr" value="hr"> 人事管理</label>
        <label><input type="checkbox" id="permAttendance" value="attendance"> 考勤管理</label>
    </div>
    <div style="font-size:12px;color:var(--text-secondary);margin-top:4px;">admin 角色自动拥有所有权限</div>
</div>
```

### JS 提交权限

```javascript
const checkedPerms = [];
if (document.getElementById('permSalary').checked) checkedPerms.push('salary');
if (document.getElementById('permHr').checked) checkedPerms.push('hr');
const permissions = JSON.stringify(checkedPerms);

// 新增时：
body: JSON.stringify({username, password, display_name, role, permissions}),

// 编辑时：
const body = {role, permissions};
```

## 权限校验验证方案

```bash
# 1. admin 登录
curl -c /tmp/admin http://host/login -X POST -d 'username=admin&password=xxx'

# 2. 验证权限隔离
# editor1（仅 salary 权限）
curl -c /tmp/editor http://host/login -X POST -d 'username=editor1&password=editor123'

# salary 路由（应 200）
curl -o /dev/null -w '%{http_code}' -b /tmp/editor http://host/salary

# contracts 路由（应 403 — 需要 hr 权限）
curl -o /dev/null -w '%{http_code}' -b /tmp/editor http://host/contracts

# 3. 更新权限后重新登录才能生效（permissions 存在 _active_tokens 中）
```

## ⚠️ 常见陷阱

1. **登录时 SQL 没取 permissions 列** — 最常见的 bug。`require_login` 的 SELECT 必须包含 `permissions`
2. **Jinja2 双引号冲突** — 在 HTML onclick 属性中嵌入 JSON 字符串时，`| e` 会转义引号。用 `data-permissions` 属性绕过
3. **重启后 session 丢失** — `_active_tokens` 是内存 dict，服务重启后所有登录用户需要重新登录才能获取 permissions
4. **修改权限后需重新登录** — `_active_tokens` 只存登录时的快照，修改权限不会同步到已有 session

## 与 role 体系的关系

| | role（传统角色） | permissions（模块权限） |
|---|---|---|
| 作用域 | 整体操作权限 | 模块级访问控制 |
| 取值 | admin/editor/viewer | ["salary", "hr"] 等 |
| admin | 最高权限 | 免检（所有路由） |
| editor/viewer | 受 permissions 限制 | 只有勾选的模块可访问 |
