---
name: fastapi-form-error-handling
category: software-development
description: 排查和修复 FastAPI 表单提交错误 — [object Object] / {file required} / Field required 类乱码提示
trigger:
  - "用户报告表单保存失败、错误提示乱码、[object Object] 或 {file required} 类错误"
  - "FastAPI 后端 validation error 显示异常"
  - "表单提交后右上角出现叉号错误提示"
  - "Pydantic 字段校验失败时前端显示不可读的错误信息"
overlaps:
  - "web-crud-application: 新建项目时使用, 不覆盖运行时调试"
---

# FastAPI 表单提交错误处理

当用户报告"保存失败、出现叉号、错误提示是乱码/`[object Object]`/`{file required}`"时，用此流程排查。

## 根因判断（三步定位）

### 1. 抓后端原始 error 结构

不要只问用户"什么错误"，直接模拟提交缺字段请求：

```bash
curl -s -X POST http://localhost:8000/api/employees \
  -H "Content-Type: application/json" \
  -d '{"name":"缺字段测试","phone":"123"}' \
  -b "session=$(curl -s -c - http://localhost:8000/login -X POST -d 'username=admin&password=admin123' | grep session | awk '{print $NF}')" | python3 -m json.tool 2>/dev/null
```

观察返回的 `detail` 字段：
- **数组** → FastAPI 自动 validation error，每个元素有 `type` / `loc` / `msg`
- **字符串** → 自定义错误，直接读

### 2. 查看前端错误渲染代码

搜索 `.catch` / `error` / `result.detail` / `errMsg` — 定位到 AJAX 回调中的错误处理分支。

常见错误：

| 现象 | 根因 |
|------|------|
| `[object Object]` | `result.detail` 是数组，直接 `+ detail` 或 `.toString()` 拼接 |
| `{file required}` | 只取 `e.msg`，但 `msg` 是英文 `Field required` 不可读 |
| 空白的叉号 | 错误处理分支没执行（catch 没触发或 try 中吞了异常） |
| 英文 `Field required` | 缺字段时 Pydantic 返回 `"msg": "Field required"`，需翻译 |

### 3. 检查前端是否缺字段或字段名不匹配

对比后端的 Pydantic `EmployeeCreate` 字段和前端 `<form>` 中 `input[name=...]` 的 `name`：
- 后端新增字段但前端没加 → 提交时缺字段
- 前端改了字段名但后端模型没改 → 提交不上去
- 前端删了字段但后端仍是必填 → validation error

## 修复方案

### 方案 A: 翻译 `missing` 类型错误（推荐）

在 AJAX 错误处理回调中，对 `result.detail` 数组逐个元素处理：

```javascript
} else if (Array.isArray(result.detail)) {
    errMsg = result.detail.map(e => {
        const fieldName = (e.loc || [])
            .filter(x => x !== 'body' && x !== 'query')
            .join('.');
        const typeLabel = {
            'missing': '缺少',
            'string_type': '类型错误',
            'type_error.str': '类型错误',
        }[e.type] || e.msg || '校验失败';
        return fieldName ? `${fieldName}:${typeLabel}` : typeLabel;
    }).join('; ');
}
```

### 方案 B: 后端改为 Optional（当字段在前端已被删除时）

如果后端 Pydantic 模型中字段前端已删除/不再使用：

```python
# 改前
department: str
# 改后
department: Optional[str] = ""
```

⚠️ 仅当前端确实没有该字段时用。如果字段还在前端只是拼写错误，优先修复拼写。

## 验证方法

模拟缺字段提交 → 检查 HTTP 状态码和错误信息是否可读：

```python
conn.request("POST", "/api/employees", json.dumps({"name":"缺字段测试"}),
             {"Content-Type":"application/json", "Cookie":f"session={session}"})
resp = conn.getresponse()
body = json.loads(resp.read().decode())
# 期望: resp.status == 422, body["detail"] 是数组且包含 type+loc
```

## Pitfalls

- **不要只看 HTTP 状态码** — 422 是正常的 validation error，不是 bug
- **不要修改后端状态码** — 还返回 200 但错误信息藏在 body 里会让前端更难处理
- **`e.msg` 是英文** — 永远不要直接显示给用户，做翻译映射
- **前端 `oninput` 冲突** — 如果表单字段有 `oninput="this.value.replace(/\\D/g,'')"` 等清理逻辑，可能和提交冲突（上次遇见过 `[object Object]`，根因是 `oninput` 返回空白字符串导致 FastAPI 收到空值）。改 `onchange` 或去掉。
- **`detail` 可能是字符串** — 自定义 `HTTPException` 可能直接返回 `{"detail": "xxx"}`，需要 `typeof result.detail === 'string'` 分支
