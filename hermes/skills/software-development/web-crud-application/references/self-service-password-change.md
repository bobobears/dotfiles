# 用户自行修改密码（个人账户页面）

## 概述

在已有 RBAC 用户系统基础上，为所有角色提供修改自身密码的能力。每个用户登录后可见「我的账户」页面，通过原密码验证后设置新密码。

## 后端实现

### 1. 个人账户页面路由

```python
@app.get("/account", response_class=HTMLResponse)
async def account_page(request: Request):
    user = await require_login(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    return HTMLResponse(render("account.html", request=request, current_user=user))
```

### 2. 修改密码 API（仅需 session token 验证身份，不依赖 admin 权限）

```python
@app.post("/api/account/change-password")
async def change_password(request: Request):
    user_info = await require_login(request)
    if user_info is None:
        raise HTTPException(401, "未登录")

    body = await request.json()
    old_pw = body.get("old_password", "")
    new_pw = body.get("new_password", "")

    if len(new_pw) < 6:
        raise HTTPException(400, "新密码至少6个字符")

    old_hash = hashlib.sha256(old_pw.encode()).hexdigest()
    new_hash = hashlib.sha256(new_pw.encode()).hexdigest()

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id FROM users WHERE username=? AND password=?",
            (user_info["username"], old_hash),
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(400, "原密码不正确")

        await db.execute("UPDATE users SET password=? WHERE id=?", (new_hash, row["id"]))
        await db.commit()

    return {"ok": True, "message": "密码已修改"}
```

### 3. 当前用户信息 API（可选，用于账户页展示）

```python
@app.get("/api/me")
async def api_me(request: Request):
    user = await require_login(request)
    if user is None:
        raise HTTPException(401, "未登录")

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, username, display_name, role, created_at FROM users WHERE username=?",
            (user["username"]),
        )
        row = await cursor.fetchone()

    if not row:
        raise HTTPException(404, "用户不存在")
    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "role": row["role"],
        "created_at": row["created_at"],
    }
```

## 前端模板（account.html）

### 页面结构

```
┌─────────────────────────────┐
│  🔑 我的账户          ← 返回首页 │
├─────────────────────────────┤
│  账户信息                     │
│  ─────────────────────────── │
│  用户名          admin       │
│  显示名称        系统管理员    │
│  角色            admin       │
├─────────────────────────────┤
│  修改密码                     │
│  ─────────────────────────── │
│  当前密码     [·········]    │
│  新密码       [·········]    │
│  确认新密码   [·········]    │
│  [保存修改]                   │
└─────────────────────────────┘
```

### 关键 JS

```javascript
async function changePw(e) {
    e.preventDefault();
    const oldPw = document.getElementById('oldPw').value;
    const newPw = document.getElementById('newPw').value;
    const confirmPw = document.getElementById('confirmPw').value;

    if (newPw !== confirmPw) { toast('两次输入的新密码不一致', 'error'); return; }
    if (newPw.length < 6) { toast('新密码至少6个字符', 'error'); return; }

    const resp = await fetch('/api/account/change-password', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({old_password: oldPw, new_password: newPw}),
    });
    // ...
}
```

### HTML 关键点

- 表单不提交到后端页面跳转，用 `fetch` + JSON
- 提交按钮在请求期间 `disabled` + 显示「保存中…」
- 成功后 `reset()` 清空表单
- 密码字段 `minlength="6"` 前端校验 + 后端二次校验

## 安全要点

| 检查项 | 说明 |
|--------|------|
| 原密码验证 | 必须验证旧密码正确才允许修改，防止 Session 被盗后的无限制改密 |
| 长度限制 | 前后端均验证 ≥6 字符 |
| 确认一致性 | 前端校验新旧密码一致，减少无效请求 |
| 角色无关性 | 所有角色均可修改自身密码，无需 admin 权限 |
| 敏感业务 | admin 修改他人密码走独立路径（用户管理页编辑），不走 `/account` 路径 |

## 效果验证

```bash
# 登录
curl -c /tmp/cookies http://localhost:8000/login -d "username=admin&password=admin123" -L

# 验证密码错误场景
curl -b /tmp/cookies -X POST http://localhost:8000/api/account/change-password \
  -H "Content-Type: application/json" \
  -d '{"old_password":"wrong","new_password":"new123456"}'
# → 400: 原密码不正确

# 正确修改
curl -b /tmp/cookies -X POST http://localhost:8000/api/account/change-password \
  -H "Content-Type: application/json" \
  -d '{"old_password":"admin123","new_password":"new123456"}'
# → {"ok":true,"message":"密码已修改"}

# 用新密码重新登录验证
curl -c /tmp/cookies2 http://localhost:8000/login -d "username=admin&password=new123456" -L -o /dev/null -w "%{redirect_url}"
# → /
```
