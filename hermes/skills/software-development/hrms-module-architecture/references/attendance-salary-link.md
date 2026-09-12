# 考勤→工资联动（attendance → salary link）

## 触发点

考勤数据保存时（`PUT /api/attendance/records`），自动联动计算加班费/扣款并写入 `salary_details`。

## 计算流程

```
考勤保存 → 读取 salary_basics(category='attendance') 单价
         → 按次数 × 单价 计算金额
         → UPSERT salary_details 对应金额字段
         → 返回 {ok: true, saved: N}
```

## 单价读取映射（重要！有历史陷阱）

`salary_basics` 中 `category='attendance'` 的 `item_key` 实际值：

| 用途 | 实际 item_key | 旧假设（已废弃） |
|------|---------------|-----------------|
| 一般加班单价 | `overtime_normal` | — |
| 节日加班单价 | `overtime_holiday` | — |
| 春节加班单价 | `overtime_spring` | — |
| 误餐单价 | `meal_allowance` | `attend_meal_std` |
| 外勤单价 | `field_allowance` | `attend_field_std` |
| 延时单价 | `delay_allowance` | `attend_overtime_std` |
| 迟到扣款单价 | `late_deduct` | `deduct_late_once` |

**读取模式**（已修复为兼容模式，2026-07-21）：
```python
params = {r[0]: int(r[1]) for r in await cur.fetchall()}
meal_rate = int(params.get("meal_allowance") or params.get("attend_meal_std", 10))
field_rate = int(params.get("field_allowance") or params.get("attend_field_std", 40))
delay_rate = int(params.get("delay_allowance") or params.get("attend_overtime_std", 5))
late_deduct = int(params.get("late_deduct") or params.get("deduct_late_once", 5))
```

## 字段映射（attendance_records → salary_details）

| attendance_records | salary_details | 计算 |
|-------------------|----------------|------|
| `attend_overtime_normal` | `att_overtime_normal_amt` | × `overtime_normal` |
| `attend_overtime_holiday` | `att_overtime_holiday_amt` | × `overtime_holiday` |
| `attend_overtime_spring` | `att_overtime_spring_amt` | × `overtime_spring` |
| `attend_meal_count` | `att_meal_allowance_amt` | × `meal_allowance` |
| `attend_field_count` | `att_field_allowance_amt` | × `field_allowance` |
| `attend_delay_count` | `att_delay_allowance_amt` | × `delay_allowance` |
| `attend_late or attend_late_count` | `deduct_late` | × `late_deduct` |
| `attend_personal` | — | 考勤页存 attendance，工资表的 deduct 在 salary_edit 另行处理 |

## 迟到字段特殊处理

**场景**：考勤独立页面（`attendance.html`）缺勤区的输入框 `data-field="attend_late"`，但联动计算需要 `attend_late_count`。

**修复**（2026-07-21）：
```python
late_ct = r.get("attend_late_count") or r.get("attend_late", 0)
```

## 考勤分区结构（attendance.html）

| 分区 | tab | 字段 |
|------|-----|------|
| 加班部分 | `section-overtime` | `attend_overtime_normal`, `_holiday`, `_spring`, `_meal_count`, `_field_count`, `_delay_count` |
| 缺勤部分 | `section-absence` | `attend_days`, `attend_late`, `attend_early`, `attend_personal`, `attend_sick`, `attend_absent` |

## 验证模式

```python
# 完整验证脚本模式（端到端）
# 1. 重置测试数据为 0
# 2. PUT 考勤记录（含加班+缺勤数据）
# 3. 检查 attendance_records 各字段
# 4. 检查 salary_details 各金额字段（按单价 × 次数 验证）
# 5. 清理测试数据
```

关键断言示例：
```python
assert r2[0] == 250.0  # 5次×50元
assert r2[1] == 200.0  # 2次×100元
assert r2[2] == 30.0   # 3次×10元
assert r2[3] == 5.0    # 1次×5元
```

参考 `hrms-module-architecture` 中「API 功能验证模式」引用 `references/api-verification-pattern.md`。

## 已知陷阱

1. **参数 item_key 与假设不符** — 实际数据库中 `category='attendance'` 参数的 `item_key` 不是后端代码最初假设的。发现时用 `or` fallback 兼容，但修复后不再需要旧 key。
2. **迟到字段名不统一** — 缺勤区 `data-field="attend_late"`，联动计算 `r.get("attend_late_count")`。已用 `or` fallback 兼容。
3. **旧进程缓存旧代码** — kill uvicorn 后 Hermes background 进程可能仍返回旧进程的响应。必须 `ss -tlnp | grep 8000` 确认实际 pid 已更换。
4. **唯一索引需在建表后创建** — `(employee_id, year, month)` 唯一索引必须在 UPSERT 之前存在。如果索引在建表时没有，后续 CREATE UNIQUE INDEX 才能启用 UPSERT。
