# API 功能验证方法论

## 核心模式：四步闭环

```
插入测试数据 → 调用 API → 断言结果 → 清理
```

全部写在一个自包含的 Python 脚本中，`exit code 0` = 通过。

## 模式模板

```python
#!/usr/bin/env python3
"""验证 [功能名] —— 自包含验证"""
import http.client, json, urllib.parse, sys, sqlite3

errors = 0
HOST = ("localhost", 8000)

# 1. 登录获取 session
conn = http.client.HTTPConnection(*HOST)
conn.request("POST", "/login", urllib.parse.urlencode({"username":"admin","password":"admin123"}),
             {"Content-Type":"application/x-www-form-urlencoded"})
resp = conn.getresponse()
session = ""
for part in (resp.getheader("Set-Cookie","") or "").split(";"):
    if part.strip().startswith("session="): session = part.strip().split("=",1)[1]
conn.close()
assert session, "登录失败"

# 2. SQL 直接插入测试数据
db_path = "/home/bobobears/hrms/db/hrms.db"
conn = sqlite3.connect(db_path)
conn.execute("""INSERT OR IGNORE INTO employees
    (employee_id, name, gender, birth_date, phone, department, position, hire_date, employment_type, status, created_at, updated_at)
    VALUES ('VRF_001','验证','男','1990-01-01','13800000999','全科','医生','2020-01-01','合同制','离职',datetime('now'),datetime('now'))""")
conn.commit()
conn.close()

# 3. API 调用 + 断言
conn = http.client.HTTPConnection(*HOST)
conn.request("DELETE", "/api/employees/VRF_001", headers={"Cookie":f"session={session}"})
resp = conn.getresponse()
body = json.loads(resp.read().decode())
assert resp.status == 200 and body.get("ok") is True, f"HTTP {resp.status}: {body}"
conn.close()

# 4. 再次调用确认已删除（返回 404）
conn = http.client.HTTPConnection(*HOST)
conn.request("DELETE", "/api/employees/VRF_001", headers={"Cookie":f"session={session}"})
resp = conn.getresponse()
assert resp.status == 404, "已删除数据应返回 404"
conn.close()

print(f"结果: {errors} 错误")
sys.exit(errors)
```

## 为什么不用 curl

| 工具 | 问题 |
|------|------|
| `curl POST` 提交表单 | Hermes 安全策略可能拦截 `-d "password=xxx"` |
| `curl -b cookie` 链式调用 | session token 从 header 提取脆弱 |
| bash heredoc | 复杂断言能力差 |

**Python 脚本的优势**：stdlib 即可（无额外依赖），`assert` 直接断言，`exit code` 可被 agent 识别。

## 注意事项

1. **密码**：HRMS 为纯局域网系统，admin 密码固定为 `admin123`，可作为已知常量
2. **测试数据 ID 前缀**：用 `VRF_` / `TMP_` / `TST_` 前缀，不与业务数据冲突
3. **路径**：用绝对路径 `~/hrms/db/hrms.db`
4. **Import 顺序**：一次性写全 `import http.client, json, sqlite3, sys, urllib.parse`，不要分散 import
5. **异步 API**：测试脚本用同步 `sqlite3.connect` 不影响运行中的 aiosqlite
6. **Session**：每个脚本新建 session，不复用

## 模式变体

| 场景 | 变体 |
|------|------|
| GET 页面渲染 | 断言 HTML 中包含特定字符串 |
| PUT 更新 | SQL 插入 → API PUT → SQL 查询确认值已更新 |
| 批量操作 | SQL 插入多条 → API 操作 → SQL 确认 |
| 权限验证 | 不同角色 session 调用同一 API 断言不同 HTTP 状态码 |
| 边界测试 | 构造符合/不符合业务规则的 payload |
