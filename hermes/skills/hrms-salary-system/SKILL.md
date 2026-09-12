---
name: hrms-salary-system
description: HRMS 工资表扣款计算、考勤同步、薪酬参数不生效时调试。
---

# HRMS 工资系统调试

## 项目结构

```
/home/bobobears/hrms/
├── backend/main.py          # 核心逻辑（所有 API + 计算函数）
├── backend/templates/
│   ├── salary_edit.html     # 工资表编辑页
│   ├── salary_list.html     # 工资表列表页
│   └── attendance.html      # 考勤管理页
├── db/hrms.db               # SQLite 数据库
└── venv/                    # Python 虚拟环境
```

服务管理：`systemctl --user restart hrms`

## 核心计算函数（main.py）

| 函数 | 位置 | 用途 |
|------|------|------|
| `_recalc_detail(d, early_deduct_rate, absent_deduct_rate, sick_deduct_rate)` | ~L1165 | 重新计算工资明细汇总列 |
| `calc_employee_allowances(employee_id, db)` | ~L1440 | 计算四项补助（行政/岗位/技能/工龄） |
| `calc_social_housing(employee_id, db)` | ~L1302 | 计算社保和公积金扣款 |
| `_admin_level_to_key(level)` | ~L1369 | 行政级别→公积金基数映射 |

## 关键业务规则

### 扣款计算公式
- **日工资基数** = `(基本工资+技能补助+行政补助+岗位补助+工龄补助) / 21.75`
- **事假** = 日工资基数 × 天数（全额），`deduct_absent_day > 0` 时用固定金额
- **病假** = 日工资基数 × 天数 × 30%，`deduct_sick_day > 0` 时用固定金额
- **旷工** = 日工资基数 × 天数（全额）
- **早退** = `deduct_early_once` × 次数
- **迟到** = `deduct_late_once` × 次数

### 特殊人员处理
- **返聘人员**：不计工龄补助（`calc_employee_allowances` 中 `employment_type != "返聘"`）
- **劳务派遣人员**：不纳入工资表（`api_create_sheet` 和查询中排除）
- **正式员工**（合同制/聘用）：新建工资表时优先沿用上月手动值，无上月数据才从参数计算
- **返聘/临时员工**：沿用上月数据（工龄补助强制为0），无上月数据则全零
- **员工排序**：`employees.display_order` 控制固定排序，工资表/考勤表均按此排序

### 公积金基数映射
```python
{"正职": "director", "副职": "vice", "主管": "supervisor", "主办": "chargeman"}
# 对应 salary_basics 中的 fund_admin_* 参数
```

## 常见 Pitfalls

### 1. `_recalc_detail` 签名变更必须更新所有调用点
修改函数参数后，搜索 `grep -n "_recalc_detail(" backend/main.py` 找到所有调用点逐一更新。遗漏调用点会导致新参数不生效。

### 2. 薪酬参数必须从 salary_basics 表读取
不要硬编码费率。所有考勤相关参数从 `salary_basics WHERE category='attendance'` 读取。

### 3. 新建工资表 SQL 字段不存在
`SELECT sd.*, ss.sheet_id` 中 `ss.sheet_id` 不存在（`salary_sheets` 表没有 `sheet_id` 字段，只有 `id`）。应改为 `SELECT sd.*`。

### 4. 数据库关联键不一致
- `attendance_records.employee_id` 存储数据库自增 ID
- `salary_details.employee_id` 存储员工工号（字符串）
- 跨表查询必须 `JOIN employees ON employees.id = attendance_records.employee_id AND employees.employee_id = salary_details.employee_id`

### 5. API 测试需要 Token
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/login -d "username=admin&password=admin123" -c /tmp/hrms_cookie.txt | python3 -c "import sys,json;print(json.load(sys.stdin).get('access_token',''))")
curl -X POST http://localhost:8000/api/salary/sheets/24/sync-standard -H "Authorization: Bearer $TOKEN" -b /tmp/hrms_cookie.txt
```

### 6. 新建工资表必须沿用上月手动值（核心规则）
`api_create_sheet` 中正式员工的处理逻辑：**优先沿用上个月工资表的手动值**，包括 `base_salary`、`allow_admin`、`allow_position`、`allow_skill`、`allow_seniority`、`allow_special`、`allow_other`、`deduct_social`、`deduct_housing`、`deduct_other`。只有无上个月数据时才从 `salary_basics` 参数计算。返聘/临时员工同理，但工龄补助强制为0。

**用户规则：手动修改的数据绝对不被覆盖。** 如果用户手动调整了某员工的社保/公积金/补助，下个月新建工资表时必须沿用该手动值，即使与参数标准不符。例如陈东升的社保=-635.92、江浩的公积金=200，这些都是手动值，不得"修正"回标准值。

### 7. 考勤结算禁止使用 `int()` 截断小数
`api_batch_settle_attendance` 中考勤数量（如 `attend_field_count=0.5`）可能为小数。使用 `int()` 转换会截断小数部分（`int(0.5)=0`），导致金额计算错误。必须使用 `round(float(count) * rate, 2)` 计算金额。所有考勤字段（加班、餐补、外勤、延时、迟到、早退）都需要此处理。

### 8. `api_sync_standard` 是"重置为标准值"操作
`api_sync_standard`（同步标准）是用户主动触发的操作，行为是将正式员工的数据**重置为薪酬参数标准值**。这与新建工资表的"沿用上月手动值"逻辑不同。用户点了同步就是想让数据回到标准，不应阻止。

### 9. `_recalc_detail` 缺勤清零时扣款必须同步清零
旧逻辑只在"缺勤>0且扣款不足"时更新 `deduct_attend`，导致缺勤清零后旧扣款残留。必须增加 else 分支：缺勤全为0时 `deduct_attend=0`，早退为0时 `deduct_early=0`。

### 10. 前端汇总表格 input 必须有 onchange 事件
`attendance.html` 汇总表格的 `.inp-att` input 若无 `change` 事件监听，用户在表格里直接改数字不会同步到 `currentData`，保存时发送的是旧值。

## 调试流程

1. **查日志**：`journalctl --user -u hrms --no-pager -n 50`
2. **查数据**：直接查 SQLite，对比考勤表 vs 工资明细
3. **定位函数**：搜索相关关键词找到计算函数
4. **修复代码**：patch 修改
5. **语法检查**：`python3 -c "import ast; ast.parse(open('backend/main.py').read())"`
6. **重启服务**：`systemctl --user restart hrms`
7. **同步数据**：调用 sync-standard API 或手动 SQL 更新
8. **验证结果**：SQL 查询对比预期值

## 数据库关键表

| 表 | 用途 | 关键字段 |
|----|------|---------|
| `salary_sheets` | 工资表主表 | id, year, month, status |
| `salary_details` | 工资表明细 | sheet_id, employee_id(工号), 各类金额字段 |
| `salary_basics` | 薪酬参数 | item_key, item_value, category |
| `attendance_records` | 考勤记录 | employee_id(数据库ID), year, month |
| `employees` | 员工档案 | id, employee_id(工号), name, employment_type, admin_level, display_order |

## 前端模板修改

- 考勤列显示：`salary_edit.html` 中 `attend-total` 的 Jinja2 表达式
- 扣发弹窗：`salary_edit.html` 中 `popover-row` 的 input 元素
- 排序：后端 ORDER BY 控制，前端不处理排序
