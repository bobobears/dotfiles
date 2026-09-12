# "None" 字符串陷阱 — Python 数据库字段值的假空

## 现象

页面部门/岗位列显示文字 `"None"`（而非"-"或空白），且组合逻辑未触发。

## 根因

数据库字段中存储的是 Python 字符串 `"None"`（来自 `str(None)` 写入），而非 SQL `NULL` 或空字符串 `""`。

```sql
-- SQLite 中 'None' 是一个包含4个字符的字符串，不是 NULL
SELECT 'None' IS NULL;  -- 0 (false)
SELECT '' IS NULL;      -- 0 (false)
SELECT NULL IS NULL;    -- 1 (true)
```

## 影响范围

Python 的 falsy 判断（`if not value:`）对字符串 `"None"` **完全失效**：

```python
v = "None"
if not v:          # False —— "None" 是 truthy 字符串！
    print("不会执行")
    
v = None           # Python None
if not v:          # True —— 正常触发
    print("会执行")
```

同样受影响的还有 `COALESCE`、`NULLIF` 等 SQL 函数——它们只处理 SQL `NULL`，不处理字符串 `"None"`。

## 检测

```bash
# 检查哪些列有问题
sqlite3 db/hrms.db "SELECT COUNT(*) FROM employees WHERE 
    department='None' OR admin_dept='None' OR admin_position='None' 
    OR tech_dept='None' OR tech_position='None'"
```

## 修复

### 方案A：数据库层清理（推荐，一次解决所有下游问题）

```bash
sqlite3 db/hrms.db "
UPDATE employees SET department='' WHERE department='None';
UPDATE employees SET admin_dept='' WHERE admin_dept='None';
UPDATE employees SET admin_position='' WHERE admin_position='None';
UPDATE employees SET tech_dept='' WHERE tech_dept='None';
UPDATE employees SET tech_position='' WHERE tech_position='None';
"
```

优点：修复后 `COALESCE`、`NULLIF`、Python `if not` 全部正常工作。

### 方案B：Python 端防御（作为双层保障）

在组合/处理字段值的代码中加入统一清理：

```python
def _clean_field(v):
    """将 None/None/空/null/无 统一为空字符串"""
    if v is None:
        return ""
    if isinstance(v, str) and v.strip().lower() in ("", "none", "无", "null"):
        return ""
    return v

# 批量清理
for k in ("department", "position", "admin_dept", "admin_position", "tech_dept", "tech_position"):
    d[k] = _clean_field(d.get(k))
```

## 为什么会产生"None"字符串

这种情况通常发生在：

1. **Flask/FastAPI 表单提交**：前端未填写的可选字段提交时，Python 可能用 `None` 填充，然后 `str(None)` 被写入 SQLite
2. **Pandas 数据处理**：`df.fillna('None')` 等替换操作
3. **JSON 序列化/反序列化**：`json.dumps(None)` → `"null"`，但某些库可能转成 `"None"`

## 历史记录

- 2026-07-22：首次在 HRMS 员工列表页发现。张昌义、陈东升、娄蓉等6人 department 字段值为字符串 `"None"`，导致页面显示 `None` 文字。修复方式：方案A（数据库清理）+ 方案B（后端增加防御性清理）。
