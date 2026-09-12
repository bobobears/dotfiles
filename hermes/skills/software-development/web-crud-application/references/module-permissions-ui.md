# 模块权限勾选面板（前端实现）

## 场景

在 `/admin/users` 页面中，编辑用户时需要一个权限勾选面板——以 checkbox 形式列出系统所有模块，管理员勾选即为用户授予对应模块权限。

## 后端前提

1. `users` 表已有 `permissions TEXT` 字段（JSON 数组）
2. `PUT /api/admin/users/{id}` 路由已能接收 `permissions` 字段并存储

## 模块列表定义

在 `main.py` 中定义一个全局模块列表，同时在 `/admin/users` 页面 API 返回：

```python
MODULES = [
    {"id": "salary", "label": "薪酬管理"},
    {"id": "hr", "label": "人事管理"},
]

# GET /admin/users 页面渲染时传入
return HTMLResponse(render("admin_users.html",
    users=users,
    current_user=user,
    modules=MODULES,
))
```

## 前端实现（admin_users.html）

### 用户表格中的权限列

```html
<th>权限</th>
{% for u in users %}
<tr>
    <td>
        {% set perms = u.permissions|from_json %}
        {% for m in modules %}
            <span class="badge {{ 'badge-active' if m.id in perms else 'badge-inactive' }}">
                {{ m.label }}
            </span>
        {% endfor %}
    </td>
</tr>
{% endfor %}
```

需要在 Jinja2 环境下注册 `from_json` 过滤器：

```python
# main.py — 在 _jinja_env 初始化后添加
_jinja_env.filters['from_json'] = lambda s: json.loads(s) if s else []
```

### 编辑弹窗中的勾选面板

```html
<div class="form-group">
    <label>模块权限</label>
    <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:4px;">
        {% for m in modules %}
        <label style="display:flex;align-items:center;gap:4px;font-size:13px;cursor:pointer;
                      padding:4px 10px;border:1px solid var(--border);border-radius:6px;
                      background:var(--bg);user-select:none;
                      {{ 'background:#dbeafe;border-color:var(--primary);' if m.id in perms else '' }}"
               class="perm-label" data-perm="{{ m.id }}">
            <input type="checkbox" value="{{ m.id }}"
                   {{ 'checked' if m.id in perms else '' }}
                   onchange="this.parentElement.style.background=this.checked?'#dbeafe':'var(--bg)';
                            this.parentElement.style.borderColor=this.checked?'var(--primary)':'var(--border)';">
            {{ m.label }}
        </label>
        {% endfor %}
    </div>
</div>
```

### JS 提交时收集选中权限

```javascript
function saveUser(userId) {
    const permLabels = document.querySelectorAll('.perm-label');
    const permissions = Array.from(permLabels)
        .filter(lbl => lbl.querySelector('input[type="checkbox"]').checked)
        .map(lbl => lbl.dataset.perm);
    // 构造 JSON 数组字符串
    const data = {
        permissions: JSON.stringify(permissions),
        // 其他字段...
    };
    fetch(`/api/admin/users/${userId}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data),
    })
    .then(r => r.json())
    .then(resp => { if(resp.ok) location.reload(); });
}
```

## 验证要点

| 检查项 | 期望 |
|--------|------|
| 新用户在编辑页打开时未勾选任何权限 | ✅ 空数组 `[]` |
| 勾选「薪酬管理」保存后表格显示蓝色 badge | ✅ |
| 取消全部勾选保存 | ✅ 保存 `[]` 到数据库 |
| admin 用户编辑页 | ✅ 权限 checkbox 可显可改（实际业务中 admin 免检，但可在此查看和调整） |
| 无该模块权限的用户尝试访问 protected 路由 | ✅ 被 `require_permission` 拒绝 |

## 验证注意事项

### display:none 检测的上下文窗口

验证脚本检测导航链接是否隐藏时，上下文窗口不能过大。如果搜索 `display:none` 的 range 设为 `m.start()-200`，会**包含前一个链接**的 `display:none`（如合同管理的隐藏样式被收入薪资标准链接的 range），导致假阳性。

**正确做法**：验证脚本中检测 `display:none` 时，range 不超过 `m.start()-5`：

```python
# ❌ 错误：包含前一个链接的 display:none
'display:none' not in html[m.start()-200:m.end()]

# ✅ 正确：只检查当前标签
'display:none' not in html[max(0,m.start()-5):m.end()]
```

### 无 emoji 的导航链接

首页（index.html）的导航按钮使用 emoji 前缀（如 `📄 合同管理`），但其他页面（salary_list、salary_standards）的 `header-nav` 中导航链接**没有 emoji**，只有纯文本（如 `合同管理`）。验证脚本需要同时支持两种格式：

```python
for text in ('📄 合同管理', '合同管理'):
    for m in re.finditer(rf'<a [^>]*>{re.escape(text)}</a>', html):
        ...
```
