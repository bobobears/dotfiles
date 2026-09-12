---
name: hrms-salary-calculation
description: Fix HRMS salary calc, deduction formulas, and data sync.
---

# HRMS 工资计算业务规则与数据同步

## 核心业务规则

### 病事假扣款公式（强制）

日工资基数 = **(基本工资 + 技能补助 + 行政补助 + 岗位补助 + 工龄补助) / 21.75**

扣款计算：
- 事假：`日工资基数 × 事假天数`（全额）
- 病假：`日工资基数 × 病假天数 × 30%`
- 旷工：`日工资基数 × 旷工天数`（全额）
- 早退：`早退次数 × deduct_early_once`（默认5元/次）
- 迟到：`迟到次数 × deduct_late_once`（默认5元/次）

> ⚠️ **旧公式只用了 `基本工资/21.75`，已被替换。日工资基数必须包含四项补助。**

薪酬参数中 `deduct_absent_day=0` 和 `deduct_sick_day=0` 表示使用上述默认公式。若改为固定金额（如事假每天扣100），直接修改 `salary_basics` 表中对应 `item_value` 即可。

### 返聘人员排除规则

- **返聘人员不计算工龄补助**：`calc_employee_allowances` 中 `employment_type="返聘"` 时 `allow_seniority=0`
- **劳务派遣人员不纳入工资表**：`api_create_sheet` 已排除 `employment_type="劳务派遣"`

### 公积金行政级别映射

| 行政级别 | 映射 key | 公积金基数 | 8%扣款 |
|---------|---------|-----------|--------|
| 正职 | director | 7500 | 600 |
| 副职 | vice | 5000 | 400 |
| 主管 | supervisor | 3750 | 300 |
| 主办 | chargeman | 3125 | 250 |
| 无级别 | general | 2500 | 200 |

> ⚠️ **曾出现主管/主办映射反了的bug**（主管→chargeman 3125，主办→supervisor 3750），已修复。

### 工资表人员固定排序

通过 `employees.display_order` 字段强制排序，27人固定顺序：
金驰、蔡旭凯、陈东升、陈胜、朱静涛、檀小平、朱精灵、雷童童、刘炜、占梦莹、叶圣婷、韩维娜、张雪玲、娄蓉、方珍华、董春霞、白川、马燕妮、姚万利、张昌义、陈实庆、王柳青、江爱军、潘功寅、王丰荣、张晶、江浩

## 核心函数

### `_recalc_detail(d, early_deduct_rate, absent_deduct_rate, sick_deduct_rate)`

重新计算工资明细的汇总列。所有调用点必须传入薪酬参数：

```python
# 读取薪酬参数
params = {r[0]: r[1] for r in await cur.fetchall()}  # category='attendance'
absent_deduct = float(params.get("deduct_absent_day", 0))
sick_deduct = float(params.get("deduct_sick_day", 0))
early_rate = float(params.get("deduct_early_once", 5))

_recalc_detail(row, early_deduct_rate=early_rate, absent_deduct_rate=absent_deduct, sick_deduct_rate=sick_deduct)
```

**所有调用点**（6处）：
1. `api_create_sheet` — 新建工资表（非正式员工路径）
2. `api_sync_standard` — 同步薪酬标准
3. `api_batch_save_attendance` — 考勤保存
4. `api_batch_settle_attendance` — 结算考勤
5. `api_update_salary_detail` — 更新单个字段
6. `api_update_attendance` — 弹窗保存考勤天数

### `calc_employee_allowances(employee_id, db)`

自动计算四项补助。已排除返聘人员的工龄补助。

### `calc_social_housing(employee_id, db)`

计算社保和公积金。公积金基数通过 `_admin_level_to_key()` 映射行政级别。

## 核心业务规则（续）

### 手动修改值优先原则（强制）

**用户手动修改的数值，后续月份必须沿用，不得被系统自动覆盖。**

受影响字段：`base_salary`, `allow_admin`, `allow_position`, `allow_skill`, `allow_seniority`, `allow_special`, `allow_other`, `deduct_social`, `deduct_housing`, `deduct_other`

实现方式：
- **新建工资表**（`api_create_sheet`）：正式员工优先从上月工资表复制完整值，无上月数据才从参数计算
- **结算考勤**（`api_batch_settle_attendance`）：**不覆盖** `deduct_social`, `deduct_housing`, `deduct_other` 字段
- **同步标准**（`api_sync_standard`）：用户主动触发，会重置为标准值（这是预期行为）

### 考勤结算的小数精度问题

`api_batch_settle_attendance` 中计算考勤金额时**禁止使用 `int()` 转换数量**，否则 0.5 次外勤会被截断为 0：

```python
# ❌ 错误：int(0.5) = 0
sd_dict["attend_field_allowance"] = int(f_c) * field_rate

# ✅ 正确：保留小数
sd_dict["attend_field_allowance"] = round(float(f_c) * field_rate, 2)
```

所有考勤字段（加班、餐补、外勤、延时、迟到、早退）都必须用 `round(float() * rate, 2)`。

### `_recalc_detail` 缺勤清零 bug（强制修复）

当缺勤天数全部为 0 时，`deduct_attend` 和 `deduct_early` **必须清零**。旧逻辑只处理了"增加扣款"的情况，导致缺勤清零后旧扣款残留：

```python
# ❌ 旧逻辑：只在缺勤 > 0 且扣款不足时更新，缺勤清零后旧扣款残留
if (days_personal + days_sick + days_absent) > 0 and current_deduct < calc_attend_deduct:
    d["deduct_attend"] = calc_attend_deduct

# ✅ 正确逻辑：缺勤有值时填充，缺勤清零时扣款也清零
if (days_personal + days_sick + days_absent) > 0:
    if current_deduct < calc_attend_deduct:
        d["deduct_attend"] = calc_attend_deduct
else:
    d["deduct_attend"] = 0

# 早退同理
if early_count > 0:
    if current_early < calc_early_deduct:
        d["deduct_early"] = calc_early_deduct
else:
    d["deduct_early"] = 0
```

### 前端考勤录入的 removeField 逻辑

`attendance.html` 中 `removeField()` 必须**直接设为 0**，而非恢复原始值。同时 `addEntry()` 初始化 `currentData[eid]` 时必须从 `originalData[eid]` 深拷贝，否则已有字段会被全零覆盖。

### 前端汇总表格 input 缺少 onchange 事件

`attendance.html` 汇总表格的 `.inp-att` input **必须有 `change` 事件监听**，否则用户在表格里直接改数字不会同步到 `currentData`，保存时发送的还是旧值。

## 数据同步模式

### api_create_sheet 的 SQL 陷阱

`SELECT sd.*, ss.sheet_id` 会导致 `sqlite3.OperationalError: no such column: ss.sheet_id`。正确写法：

```sql
SELECT sd.* FROM salary_details sd
JOIN salary_sheets ss ON sd.sheet_id = ss.id
WHERE ss.year=? AND ss.month=?
```

### sync_standard API 的 deduct 字段写回

`api_sync_standard` 调用 `_recalc_detail` 后，**必须写回 `deduct_attend` 和 `deduct_early`**，否则扣款只更新了内存中的 dict 而没有持久化。

### 修改业务规则后的数据同步流程

1. 修改代码（`_recalc_detail` 或相关函数）
2. 重启服务：`systemctl --user restart hrms`
3. 清零旧扣款：`UPDATE salary_details SET deduct_attend=0, deduct_early=0 WHERE ...`
4. 调用 sync-standard API：`POST /api/salary/sheets/{id}/sync-standard`
5. 手动处理返聘人员（sync_standard 跳过非正式员工）
6. 验证：对比考勤表 vs 工资明细

### 数据库关联特性

- `attendance_records.employee_id` 存储数据库自增ID（`employees.id`）
- `salary_details.employee_id` 存储员工工号（`employees.employee_id`，字符串）
- 跨表查询必须通过 `employees` 表桥接

## 前端显示

### 考勤列

考勤列显示 = **加班津贴 - 缺勤扣款**，直接反映考勤对工资的净影响。

### 扣发弹窗

必须包含迟到/早退/事假独立行，按以下分组：
- 考勤缺勤扣款：迟到扣款、早退扣款、事假/病假/旷工
- 法定扣款：社保个人、公积金个人
- 其他扣款

## 已知缺陷修复记录

| 缺陷 | 修复方式 |
|------|---------|
| 主管/主办公积金映射反了 | `_admin_level_to_key` 中 supervisor↔chargeman 对调 |
| sync_standard 不写回 deduct 字段 | UPDATE 语句增加 deduct_attend/deduct_early |
| 旧公式只用基本工资 | `_recalc_detail` 日工资基数包含四项补助 |
| 返聘人员有工龄补助 | `calc_employee_allowances` 排除 `employment_type="返聘"` |
| 新建工资表不沿用上月手动值 | `api_create_sheet` 正式员工优先复制上月数据 |
| 结算考勤覆盖手动社保/公积金 | `api_batch_settle_attendance` UPDATE 移除 deduct_social/deduct_housing/deduct_other |
| 考勤小数被截断（0.5次变0） | 所有考勤计算用 `round(float() * rate, 2)` 替代 `int()` |
| 前端 removeField 恢复原始值 | 改为直接设为 0 |
| 前端 addEntry 覆盖已有字段 | 从 `originalData[eid]` 深拷贝而非新建全零对象 |
| 前端汇总表格 input 无 onchange | 添加 change 事件监听同步到 currentData |
| api_create_sheet SQL 报错 | 移除 `ss.sheet_id` 字段引用 |
| 缺勤清零后扣款残留 | `_recalc_detail` 增加 else 分支清零 deduct_attend/deduct_early |
