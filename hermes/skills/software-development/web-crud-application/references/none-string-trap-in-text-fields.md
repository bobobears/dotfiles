# None 字符串陷阱：TEXT 字段存储了字面 `"None"`

## 场景

在 Web CRUD 系统中，select 下拉框或 radio 按钮在**未选中任何选项时**，前端 JS 可能会提交字符串 `"None"`（而非 Python 的 `None` 值或空字符串 `""`）。存入 SQLite TEXT 列后，显示或条件判断时会被误认为有值。

## 诊断

```bash
# 对比 Python None 和 SQLite 中的字面 'None'
sqlite3 db/hrms.db "SELECT id, name, admin_dept, LENGTH(admin_dept) FROM employees WHERE admin_dept IS NOT NULL"
```

- `admin_dept IS NOT NULL` 仍然匹配到字面 `'None'`（因为它是非 NULL 字符串）
- `LENGTH(admin_dept)` 对 SQLite 来说是真实的字符长度（`None` = 4）

## 典型表现

| 代码 | 行为 |
|------|------|
| `if not d.get("field"):` | 空字符串 `""` 和 Python `None` 被判定为假，但字符串 `"None"` 为真 |
| `if field and field.strip():` | 同上，`"None"` 通过检查 |
| `{{ field or '—' }}` | 显示 `None` 而非 `—`（用户看到 `None` 字样） |

## 修复

### 方案 A：在 Python 端过滤（推荐，不改数据库）

```python
def clean_field(val):
    """过滤空值、None字符串、'无'等无意义值，返回空字符串"""
    if not val:
        return ""
    stripped = val.strip()
    if stripped.lower() in ("none", "无", "null", "(无)"):
        return ""
    return stripped

# 使用
department = clean_field(d.get("department"))
# 或组合多个字段
parts = [clean_field(d.get("admin_dept")), clean_field(d.get("tech_dept"))]
parts = [p for p in parts if p]  # 去掉空值
```

### 方案 B：在 SQL 层过滤（适合批量展示）

```sql
-- 把 'None' 视为 NULL
SELECT id, name,
       NULLIF(admin_dept, 'None') AS admin_dept_clean
FROM employees;
-- 或更严格
SELECT id, name,
       CASE WHEN admin_dept IN ('None', '无', 'null', '(无)') THEN NULL ELSE admin_dept END AS admin_dept_clean
FROM employees;
```

### 方案 C：修复数据源（一劳永逸）

```sql
UPDATE employees SET admin_dept = NULL WHERE admin_dept = 'None';
UPDATE employees SET tech_dept = NULL WHERE tech_dept = 'None';
```

但注意：如果是因为前端提交逻辑有 bug，修复数据后下次编辑保存又会写入 `"None"`。

## 预防

- 前端 JS 提交时，select 未选中用空字符串 `""` 而非 `"None"`
- 后端 Pydantic model 中，对应字段用 `Optional[str] = None` 或 `Optional[str] = ""`，且 validator 中把 `"None"` 转换为 `None`：

```python
@field_validator("admin_dept", mode="before")
@classmethod
def clean_none_string(cls, v):
    if v is None or v.strip().lower() in ("none", "无", "null"):
        return ""
    return v.strip()
```

## 相关场景：默认下拉值问题

很多表单使用 `<option value="">请选择</option>`，但 JS 提交时如果 `select.value` 为空字符串，基本没问题。问题是某些 UI 框架或旧版浏览器在 select 未手动选择时，`value` 可能是 `"None"`（字符串）而非 `""`。检查调试：

```javascript
// 提交前
console.log({admin_dept: document.getElementById('admin_dept').value});
// 如果输出 "None" 而非 ""，就是这个问题
```

## 本 HRMS 项目中的实际案例

2026-07-21：首页员工列表部门/岗位字段大量显示 `-`。原因是：
1. SQL SELECT 只查了 `department`/`position`，没有查 `admin_dept`/`tech_dept`/`admin_position`/`tech_position`（这些才是编辑表单实际填写的字段）
2. 补查后，Python 端 `if not d.get("department"):` 本应触发组合逻辑，但因为 SQLite 中存储的是字面字符串 `"None"`（非空非 NULL），`not "None"` 为 `False`，所以组合逻辑没执行
3. 修复：在组合逻辑的前置判断和 parts 过滤中同时排除 `"None"` 和 `"无"` 字符串

```python
# 过滤非法值
parts = [x for x in [d.get("admin_dept"), d.get("tech_dept")]
         if x and x.strip() and x.strip().lower() not in ("none", "无")]
```
