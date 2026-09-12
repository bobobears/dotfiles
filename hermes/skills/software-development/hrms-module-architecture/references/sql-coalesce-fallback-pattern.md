# ⚠️ 部门字段显示 — 组织归属组合模式（行政+技术）

## 背景

HRMS 员工的「组织归属」分为**行政归属**和**技术归属**两个子分类：

| 归属 | 子分类 | 数据库字段 |
|------|--------|-----------|
| 行政归属 | 行政部门（`admin_dept`）、行政职务（`admin_position`）、行政级别（`admin_level`） | 各自独立列 |
| 技术归属 | 技术部门（`tech_dept`）、技术职务（`tech_position`） | 各自独立列 |

遗留字段 `department` 是早期单列，新架构中应为空——部门应该从行政+技术**组合**而来。

## ⚠️ 核心约束（2026-07-22 新增，来自用户明确指正）

**「各个模块需要的部门字段，对应的是组织归属下面字段的综合选择」**

这意味着：
- ❌ **不要**只回退到 `admin_dept`（忽略 `tech_dept`）——这是本参考文件最初版本犯的错误
- ✅ 部门显示 = `department`（有值时直接用）**→** `admin_dept + tech_dept`（用" / "拼接，排除空值和"无"）

> **分层模式**已不再是简单的 COALESCE 链；对于这个特定的员工数据模型，**组合模式**才是正确的。

## 组合实现（Python 层）

❌ **错误的 SQL 层方案**（只回退到 admin_dept，忽略 tech_dept）：

```sql
COALESCE(NULLIF(e.department,''), NULLIF(e.admin_dept,''), '未分配') as emp_dept
```

✅ **正确的 Python 层方案**（2026-07-22 修正后的标准模式）：

```python
_dept = emp.get("department")
if not _dept:
    parts = [x for x in [emp.get("admin_dept", ""), emp.get("tech_dept", "")] 
             if x and x.strip() and x.strip().lower() not in ("none", "无")]
    dept_display = " / ".join(parts) if parts else "未分配"
else:
    dept_display = _dept
```

## 何时用 SQL COALESCE，何时用 Python 组合

| 场景 | 推荐方式 | 原因 |
|------|---------|------|
| ORDER BY 排序 | ✅ SQL COALESCE | 取任一非空值排序即可，不影响显示 |
| SELECT 展示字段 | ✅ **Python 组合** | SQL 无法灵活做"排除无值后拼接" |
| 下拉框列表 | ✅ Python 组合 | 同上 |

**ORDER BY 的 SQL 写法**（只做排序，不影响显示）：

```sql
ORDER BY COALESCE(NULLIF(e.department,''), NULLIF(e.admin_dept,''), NULLIF(e.tech_dept,''), ''), e.name
```

## 全项目扫描步骤

### 第1步：找出所有引用点

```bash
grep -n "e\\.department\\|department.*emp_dept\\|COALESCE.*admin_dept" backend/main.py
```

### 第2步：区分需要改的点

| 类型 | 需要改？ | 处理方式 |
|------|---------|---------|
| SELECT `COALESCE(..., admin_dept, ...) as emp_dept` | ✅ 必须改 | 改为取原始字段 + Python组合 |
| ORDER BY `COALESCE(...)` | ❌ 不改 | 仅用于排序，不影响显示 |
| SELECT 只取 `department` 且 Python 已有组合逻辑 | ❌ 不改 | 如首页路由第338-348行 |

### 第3步：涉及的模块（全项目清单 2026-07-22）

| 模块 | 状态 | 说明 |
|------|------|------|
| 考勤页 `/attendance` | ✅ Python 组合 | SQL 取 department/admin_dept/tech_dept，第1837行组合 |
| 工资标准页面 `/salary/standards` | ✅ Python 组合 | 第1400行组合 |
| 工资明细页面 `/salary/{id}` | ✅ Python 组合 | 第1801行组合 |
| 工资API `/api/salary/sheets/{id}/details` | ✅ Python 组合 | 第2234行组合 |
| 工资标准API `/salary/standards/data` | ✅ Python 组合 | 第1448行组合 |
| 合同列表 `/contracts` | ✅ Python 组合 | 第852行组合 |
| 合同详情 `/contracts/{id}` | ✅ Python 组合 | 第965行组合 |
| 员工列表首页 `/` | ✅ Python 组合 | 已存在，第343行 |
| 薪资标准下拉框 | ✅ Python 组合 | 第1402行 on all_emps |

### 第4步：验证

用页面浏览验证（不是 SQL 查询，因为组合逻辑在 Python 端）：
- 打开考勤、工资标准、合同列表等页面
- 检查有无空白部门列（`<td></td>`）
- 检查 admin_dept 和 tech_dept 之一有值的员工是否显示组合结果

## 常见陷阱

1. **只回退到 admin_dept** — 忽略了 tech_dept。这是本参考文件最初版本的错误，2026-07-22 已被用户指正修复。
2. **在 SQL 层用 COALESCE** — SQL 的 `COALESCE` 只能取一个字段回退，无法做"A 或 B 都有值则拼接"的逻辑。必须在 Python 层处理。
3. **遗漏 API 端点** — 除了页面路由，JSON API 端点（如 `/salary/standards/data`、`/api/salary/sheets/*`）也需要同样的组合逻辑。
4. **`department` 字段的歧义** — 它既可能是数据库中取出的原始值，也可能是已经过 Python 组合后的显示值。建议代码中明确用 `emp_dept` 或 `dept_display` 做变量名区分显示值。
5. **前端 form.html 中的组织归属多层结构** — 编辑页面使用 `admin_dept/行政部, admin_position/行政职务, admin_level/行政级别, tech_dept/技术部门, tech_position/技术职务` 五个独立下拉/输入框。后端存储各自独立。**只在显示时组合，不要在编辑时合并。**
