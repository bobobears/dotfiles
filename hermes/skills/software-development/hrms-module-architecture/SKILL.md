---
name: hrms-module-architecture
description: "HRMS 模块扩展方案：当需要在现有人事系统中新增功能模块时，判断是新开页面还是在原有页面添加。含薪酬模块完整数据模型、工资表操作流程、模块级权限隔离方案（permissions JSON数组）、以及后端开发常见陷​阱。"
version: 1.0.0
platforms: [linux]
---

# HRMS 模块扩展 —— 页面结构决策

## 判断原则

| 特征 | 适合新页面 | 适合原有页面 |
|------|-----------|-------------|
| 与员工是 1:N 关系（一个员工多条记录） | ✅ 新页面 | — |
| 有独立生命周期（到期、续签、变更等） | ✅ 新页面 | — |
| 需要跨员工筛选/查看/操作 | ✅ 新页面 | — |
| 只是员工基本资料的扩展属性（1:1） | — | ✅ 原有页面加字段 |
| 只读展示关联信息 | — | ✅ 详情页加展示区块 |

## 推荐菜单结构

```
菜单：
├── 人事管理（现有）
│   ├── 员工列表（首页）
│   ├── 新增/编辑员工
│   ├── 离职人员查询
│   └── ...
├── 合同管理（新）
│   ├── 合同列表（可筛选到期、按部门）
│   └── 合同详情/续签
├── 薪酬标准（新）
│   ├── 薪酬标准维护
│   ├── 调薪记录
│   └── 批量调薪
└── ...
```

## 模块间关联方式

- 各模块以 `employee_id` 为外键关联
- 员工详情页底部留「关联信息」区块（只读展示+跳转链接）
- 不在详情页塞管理操作——详情页是展示入口，管理操作在独立模块进行

## 薪酬模块参考设计

当需要新增「薪酬管理」模块时，业务流程和数据模型参考以下设计。

### 业务需求常见模式（本用户）

来自实际需求澄清的用户偏好（2026-07-18 本次会话确认）：

| 维度 | 偏好 |
|------|------|
| 工资构成 | **应发** = 基本工资 + 补助(6项) + 考勤(4项) + 绩效(2项)；**扣发** = 考勤扣发 + 社保个人 + 公积金个人 + 其他扣款(可添加) |
| 补助项 | 固定6项：行政补助、岗位补助、技能补助、工龄补助、特别补助、其他补助 |
| 其他补助明细 | 可添加多笔，每笔含 `amount` + `note`（备注），JSON 存储 |
| 考勤项(应发) | 误餐津贴、外勤津贴、延时津贴、加班工资（每月手动填） |
| 绩效项 | 公卫计件、其他（每月手动填，从工作量报表导入后微调） |
| 社保/公积金 | 基数+缴交比例 → 自动计算个人代缴额。每年手动调整一次 |
| 考勤扣发 | 合计值（迟到/早退、病假/事假、考勤缺失整合为单项） |
| 其他扣款 | 可添加多笔，每笔含 `amount` + `note`，JSON 存储，**不单独建子表** |
| 每月发薪 | 基于上月数据生成 → 人工微调 → 确认发放 |
| 绩效来源 | 从外部系统(工作量报表)导入，手动微调 |
| 基本工资 | 每个员工单独设置（薪酬档案），不是简单按岗位自动 |
| 社保/公积金 | 每年调整一次基数，手动设置 |
| 周期 | 按月，每月一批 |

### 推荐数据模型（三表，salary_standards 已移除）

**架构变更（2026-07-25）**：`salary_standards` 表已被移除。原因是该表存储的31条记录中，所有金额字段（allow_admin/position/skill/seniority、social_base、housing_fund_base、base_salary）的值**100% 可由 employees 属性字段 + salary_basics 等级表实时计算得出**，不存在任何个性化偏离。allow_special 和 allow_other 全员为 0。唯一有价值的内容是 31 条 notes，已迁移至 `employees.salary_notes`。

**新数据流**：
```
employees(属性字段) + salary_basics(等级参数表)
       ↓ calc_employee_allowances() 实时计算
salary_details(每月工资明细)
```

**① employees 表薪资相关字段**（替代原 salary_standards）

| 字段 | 类型 | 说明 |
|------|------|------|
| admin_level | TEXT | 行政级别（正职/副职/主管/主办/None）→ 匹配 salary_basics 行政补助等级 |
| tech_position | TEXT | 技术职务（含"医生"→岗位补助） |
| qualification | TEXT | 职称（高级/副高/中级/初级/无）→ 匹配 salary_basics 技能补助等级 |
| hire_date | TEXT | 入职日期 → 计算工龄 → 匹配 salary_basics 工龄补助等级 |
| salary_notes | TEXT | 薪资备注（从原 salary_standards.notes 迁移） |

**② salary_basics 表**（单位级参数，不变）

所有补助等级、社保/公积金参数、考勤标准均在此表。`calc_employee_allowances()` 从此表读取等级映射，结合 employees 属性字段实时计算。

**③ salary_sheets / salary_details**（月度工资表，不变）

创建工资表时，直接调用 `calc_employee_allowances()` 为每人生成补助数据，不再经过 salary_standards 中间层。

**② salary_sheets（月度工资表）** — 每月一条

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK AUTO |
| year | INTEGER | 年份 |
| month | INTEGER | 月份 |
| status | TEXT | 草稿 / 已确认 / 已发放 |
| total_gross | REAL | 应发总额 |
| total_deduct | REAL | 扣款总额 |
| total_net | REAL | 实发总额 |
| created_at | TEXT | 创建时间 |

**③ salary_details（月度工资明细）** — 每人每月一条

**应发部分：**

| 字段 | 类型 | 来源 |
|------|------|------|
| base_salary | REAL | 从标准复制或手动 |
| allow_admin | REAL | 从标准复制 |
| allow_position | REAL | 从标准复制 |
| allow_skill | REAL | 从标准复制 |
| allow_seniority | REAL | 从标准复制 |
| allow_special | REAL | 从标准复制 |
| allow_other | REAL | 从标准复制 |
| allow_other_json | TEXT | JSON数组 `[{"amount":200,"note":"交通补助"},...]` |
| attend_meal | REAL | 每月手动填（误餐津贴） |
| attend_field | REAL | 每月手动填（外勤津贴） |
| attend_overtime | REAL | 每月手动填（延时津贴） |
| attend_extra | REAL | 每月手动填（加班工资） |
| perf_public_health | REAL | 每月手动填（公卫计件） |
| perf_other | REAL | 每月手动填（其他绩效） |

**扣发部分：**

| 字段 | 类型 | 来源 |
|------|------|------|
| deduct_attend | REAL | 每月手动填 |
| deduct_social | REAL | 自动计算（基数×比例） |
| deduct_housing | REAL | 自动计算（基数×比例） |
| deduct_other | REAL | 每月手动填 |
| deduct_other_json | TEXT | JSON数组 `[{"amount":xxx,"note":"..."}]` |

**自动计算字段：**
**自动计算字段：**
| 字段 | 类型 | 公式 |
|------|------|------|
| total_gross | REAL | 基本工资 + 各项补助 + 考勤 + 绩效 |
| total_deduct | REAL | 考勤扣发 + 社保 + 公积金 + 其他扣款合计 |
| total_net | REAL | total_gross - total_deduct |

**⚠️ 汇总字段取整**：`_recalc_detail()` 中的 `total_gross`、`total_deduct`、`total_net` 是浮点累加，可能出现多位小数（如 `2000 + 1200 + 50.00 = 3250.0000001`）。如果前端显示异常，在 `_recalc_detail` 末尾对三个汇总字段应用 `_r2()` 取整。

### 操作流程（2026-07-27 更新，salary_standards 已移除）

```
① 新建工资表 → 选年月 → 自动生成
   → 包含所有在职员工（status != '离职'，employment_type != '劳务派遣'）
   → 正式员工（合同制/聘用）：从 salary_basics + employees 实时计算
      - 基本工资从 salary_basics.base_min 取值
      - 四项补助由 calc_employee_allowances() 计算
      - 社保/公积金由 calc_social_housing() 计算
   → 返聘/临时员工：取上个月工资表数据，社保/公积金强制为 0
   → 状态=草稿
        ↓
② 编辑草稿工资表
   → 每行员工：补助列弹出面板含6项
   → 考勤/绩效/扣发列同理弹出子项面板
   → 实时自动计算应发/实发
   → 如需重新从薪酬参数同步：底部"重新同步"按钮
        ↓
③ 保存草稿 / 确认工资表（锁定，状态=已确认）
        ↓
④ 发放（状态=已发放）→ 只读 + 可导出Excel
```

### "重新同步"按钮设计（2026-07-27 最终版）

**位置**：工资表编辑页底部操作栏，与确认按钮同行

**行为**：
1. 点击 → confirm 确认覆盖
2. POST `/api/salary/sheets/{id}/sync-standard`
3. 后端：遍历工资表明细中所有员工：
   a. 正式员工：调用 `calc_employee_allowances(eid, db)` 重新计算四项补助 + `calc_social_housing(eid, db)` 重新计算社保/公积金
   b. 基本工资从 salary_basics `base_min` 取值
   c. 返聘/临时员工：保持不变
4. 成功 → toast + 页面 reload

**数据来源**：所有数据直接从 `employees` 属性字段 + `salary_basics` 等级表实时计算。

**用户偏好**：标准修改后同步到当前工资表时**覆盖明细**（非增量合并），用户明确选择了"从标准重新复制到当前工资表（覆盖明细）"。

**用户偏好**：标准修改后同步到当前工资表时**覆盖明细**（非增量合并），用户明确选择了"从标准重新复制到当前工资表（覆盖明细）"。

### ⚠️ 入职日期过滤：新建工资表时排除未来入职的员工

**问题**（2026-07-21）：孙闪闪（2026-07-06）、宁红（2026-07-13）、邱映雪（2026-07-15）7月入职，6月工资表不应包含。

**修复**：创建工资表时，SQL 查询过滤 `hire_date` 大于当月底的员工：

```python
import calendar
last_day = calendar.monthrange(y, m)[1]
hire_cutoff = f"{y:04d}-{m:02d}-{last_day}"

cur = await db.execute(
    """SELECT e.employee_id, e.name as emp_name
       FROM employees e
       WHERE e.status != '离职'
         AND (e.hire_date IS NULL OR e.hire_date <= ?)
       ORDER BY e.department, e.name""",
    (hire_cutoff,)
)
```

**原理**：当月最后一天 = `calendar.monthrange(year, month)[1]`。入职日期 > 当月底 = 下个月才来的人，不应出现在本月工资表。`hire_date IS NULL` 放宽条件防止缺数据的员工被误排除。

**注意**：已存在的工资表不会自动应用此过滤。需要手动 DELETE 掉不符合条件的 `salary_details` 行，然后更新 `salary_sheets.employee_count`。

### 代码重点：创建工资表时区分正式/非正式员工（2026-07-27）

```python
# 1) 查所有在职员工（排除劳务派遣）
cur = await db.execute(
    """SELECT e.employee_id, e.name, e.employment_type
       FROM employees e
       WHERE e.status != '离职'
         AND e.employment_type != '劳务派遣'
       ORDER BY e.department, e.name"""
)
employees = await cur.fetchall()

# 2) 为每人生成明细
for emp in employees:
    emp_type = emp["employment_type"] or ""
    is_regular = emp_type in ("合同制", "聘用", "")
    
    if is_regular:
        # 正式员工：实时计算
        allowances = await calc_employee_allowances(eid, db)
        sh = await calc_social_housing(eid, db)
        detail = {
            "base_salary": base_salary,  # 从 salary_basics.base_min
            "allow_admin": allowances["allow_admin"],
            ...
            "deduct_social": sh["deduct_social"],
            "deduct_housing": sh["deduct_housing"],
            "source": "auto_calc",
        }
    else:
        # 返聘/临时：取上个月数据或全零
        prev = prev_map.get(eid)
        ...
```

### ⚠️ 字段名差异：技能文档 vs 实际代码

| 含义 | 本文档中的字段名 | 实际代码中的字段名 |
|------|------------------|-------------------|
| 基本工资 | `basic_salary` | ✅ 一致 |
| 行政补助 | `admin_allowance` | `allow_admin` |
| 岗位补助 | `position_allowance` | `allow_position` |
| 技能补助 | `skill_allowance` | `allow_skill` |
| 工龄补助 | `seniority_allowance` | `allow_seniority` |
| 特别补助 | `special_allowance` | `allow_special` |
| 其他补助 | `other_allowance` | `allow_other` |
| 社保基数 | `social_security_base` | `social_base` |
| 个人比例 | `social_security_rate` | `social_rate` |
| 公积金基数 | `housing_fund_base` | ✅ 一致 |
| 公积金比例 | `housing_fund_rate` | ✅ 一致 |
| 社保个人扣发 | `social_security_personal` | `deduct_social` |
| 公积金个人扣发 | `housing_fund_personal` | `deduct_housing` |
| 考勤扣发 | `attendance_deduct` | `deduct_attend` |
| 应发 | `gross_pay` | `total_gross` |
| 实发 | `net_pay` | `total_net` |

在参考此文档写代码时，**以实际代码中的字段名为准**。

### 四项补助的自动等级化计算（2026-07-20 新增，2026-07-20 最终确认纯自动模式）

**设计背景**：薪资标准中的4项补助（行政/岗位/技能/工龄）根据员工档案字段自动计算等级对应金额。

**⚠️ 设计决策过程（重要）**：
1. 初始设计：自动计算 + 允许手工填写覆盖（POST 时传值为0则自动算，否则保留手动值；PUT 时保留前端传入值）
2. 用户反馈：用户要求改为**纯自动计算，不允许手动填写**。理由：数据规范统一，避免人为差异
3. 最终方案（2026-07-20）：
   - 薪资标准页面中四项补助列改为纯文本显示，标注"(自动)"
   - 新建/编辑模态框中输入框替换为只读 `<span>`
   - PUT 路由中忽略前端传入的4项补助字段，全部用服务端自动计算值覆盖
   - 提供批量管理页面 `batch_all_allowances`（/admin/batch-allowances），统一设置所有员工的行政级别/技术职务/职称/工龄等档案字段

**数据模型**：在 `salary_basics` 表新增 `grade TEXT` 字段，存储各补助的等级标识。

**四类补助等级表**（category 模式，均以 `allowance_level_` 为前缀）：

| 补助 | category | 匹配字段 | 匹配规则 |
|------|----------|----------|---------|
| 行政补助 | `allowance_level_admin` | `employees.admin_level` | 按取值精确匹配（正职/副职/主管/主办/None） |
| 岗位补助 | `allowance_level_position` | `employees.tech_position` | 含"医生"="doctor"，其余="non_doctor" |
| 技能补助 | `allowance_level_skill` | `employees.qualification` | 按取值精确匹配（高级/副高/中级/主治医师/初级/无/空） |
| 工龄补助 | `allowance_level_seniority` | `employees.hire_date` → 工龄年数 | 按区间匹配（0-4/5-9/10-14/15-19/20-24/25-29/30+） |

**工龄计算规则**：`当前年 - 入职年 - (1 if (当前月,当前日) < (入职月,入职日) else 0)`，不满1年计0。每5年一个等级区间。

**后端核心函数** `calc_employee_allowances(employee_id, db)`：
1. 查员工档案（admin_level, tech_position, qualification, hire_date）
2. 加载全部等级数据到内存 dict（避免N次SQL查询）
3. 按类型匹配等级值：
   - 行政/技能：精确匹配 `grade`，空值回退 `grade=''`
   - 岗位：关键词判断 → 固定 `grade='doctor'` 或 `grade='non_doctor'`
   - 工龄：遍历所有等级区间，找当前年数在哪个区间（`start-end` 或 `30+`）
4. 返回 `{allow_admin, allow_position, allow_skill, allow_seniority}`

**API 路由（纯自动模式，2026-07-27 更新）**：
- `GET /api/salary/standards/calc/{employee_id}` — 前端预览自动计算值（登录 required）— **已废弃**，calc_employee_allowances() 现在直接用于工资表创建
- `POST /api/salary/sheets` — 新建工资表，内部调用 `calc_employee_allowances()` + `calc_social_housing()`
- `POST /api/salary/sheets/{id}/sync-standard` — 重新同步，重新计算正式员工的补助和社保/公积金
- GET/POST `/admin/batch-allowances` — 批量管理页面：所有员工的行政级别/技术职务/职称/工龄设置页面

**前端交互（纯自动模式）**：
- 薪资标准表格：4项补助列显示金额 + 标注"(自动)"，无编辑输入框
- 新建/编辑模态框：4项补助区域为只读 `<span>` 显示自动计算值，选中员工时自动 calc API 填充
- 使用 `setupCalcOnEmployeeSelect()` 函数，每次 `openAddModal()` 时替换 `<select>` 的 change 监听器（避免多次绑定）
- **编辑模态框不显示可输入框**——用户通过批量管理页面调整员工档案字段后，calc-all 批量重新计算
- **批量管理页面 `/admin/batch-allowances`**：表格显示所有员工 + 行政级别下拉 + 技术职务下拉 + 职称下拉 + 工龄（只读，由 hire_date 自动计算）。提交后自动调用 calc-all 刷新薪资标准

**工龄显示**：
- 员工编辑页（form.html）：入职日期输入框右侧显示 `<span id="seniority_display">`，页面加载和日期变化时通过 JS 实时计算显示"工龄 X 年"
- 员工详情页（view.html）：Jinja2 模板中使用 `{% set %}` 计算工龄并显示

**种子数据示例**（默认金额）：
```
行政补助: None→100, 主办→200, 主管→400, 副职→600, 正职→800
岗位补助: 医生→500, 非医生→200
技能补助: 无→0, 初级→200, 中级/主治→400, 副高→600, 高级→800
工龄补助: 0-4年→0, 5-9年→100, 10-14年→200, ...每5年+100→30年+→600
```
所有金额可在「薪酬参数」页面自由修改，修改后自动计算立即生效。

### 薪酬基本参数模块（`salary_basics`）— 新增

**定位**：全单位统一的参考参数表，是薪酬计算的唯一参数来源（salary_standards 表已于 2026-07-25 移除）。

**核心设计**：
- 单表 `salary_basics`（category, item_key, item_name, item_value, unit, description, grade）
- 分类包括：base_salary（基本工资参考）、allowance_level_*（补助等级）、social_security（社保比例/基数）、housing_fund（公积金比例/基数）、attendance（考勤标准）
- 补助等级表：`allowance_level_admin`、`allowance_level_position`、`allowance_level_skill`、`allowance_level_seniority` 四个分类，每行含 grade 字段标识等级
- 行内编辑：点击数值 → input → 回车 PUT 保存
- 权限：与工资表同组（`salary`）

**示例参数**（41 条，8 分类，2026-07-21 现状）：
```
基本工资: base_min(0)
行政补助等级: 正职(1200)-副职(800)-主管(400)-主办(200)-一般人员(0)
岗位补助等级: 医生(200)-非医生(0)
技能补助等级: 高级(1200)-副高(700)-中级(400)-初级(200)-无(0)-其他(0)
工龄补助等级: 30+(600)-25-29(500)-20-24(400)-15-19(300)-10-14(200)-5-9(100)-0-4(0)
社保: ss_pension_rate(8%), ss_medical_rate(2%), ss_unemploy_rate(0.5%)
      工伤保险(0%), 生育保险(0%), 基数下限(4311), 基数上限(0)
公积金: hf_employee_rate(8%), hf_employer_rate(8%)
       正职工积金基数(7500)-副职工积金基数(5000)-主管公积金基数(3750)-主办公积金基数(3125)-无级别公积金基数(2500)
       ↑ 注意：公积金基数已从原来的"上下限"改为按行政等级分档，每条可手动调整
       曾出现过打字错误：正职/副职的"公积金"写成了"工积金"
考勤: 误餐(10/天), 外勤(40/天), 延时津贴(5/小时)
      一般加班(50/天), 节日加班(100/天), 春节加班(160/天)  ← 旧名"延时加班定额"已删除
      事假(自动计算), 病假(自动计算), 迟到扣款(5/次)
```
公式：(基本工资+技能补助+行政补助+岗位补助+工龄补助)/21.75
**注意**：
- 无"补助参考值"分类（已删除），无"其他"分类（个税起征点/加班费率已删除）
- 删除所有分类时必须同步更新模板 categories 字典和 cat_order 数组
- 操作分类级别字段后，须重启 uvicorn 进程（`ss -tlnp | grep 8000` 确认 kill 对了 pid）
- 有"自动计算"标注的字段（事假/病假扣款）在前端显示灰色斜体 `自动计算`，公式字段存描述信息，item_value 保留 0.0 占位

### 推荐页面结构

三个独立页面（薪酬模块）：

1. **`/salary`** — 月度工资表列表（年月筛选器，状态badge，新建/编辑/查看/导出）
2. **`/salary/{sheet_id}`** — 工资表编辑页（可编辑表格 + 行内弹出面板）
3. **`/salary/basics`** — 薪酬基本参数页（分组展示，行内编辑）

> **已移除**：`/salary/standards`（薪资标准管理页）— 2026-07-25 架构变更，salary_standards 表已删除。补助计算改为从 employees 属性 + salary_basics 等级表实时计算。

+ **`/attendance`** — 考勤管理模块（独立权限 `"attendance"`）

### 新增独立页面的全栈工作流

当需要在 HRMS 中新增一个独立功能模块（如考勤、合同、培训等）时，按以下步骤操作：

#### 第1步：建表（独立于主表）

```python
# 设计独立数据表，以 employee_id 为外键
# 避免在 employees 表中堆砌列
CREATE TABLE attendance_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    attend_days REAL DEFAULT 22.0,
    attend_late    REAL DEFAULT 0.0,
    attend_early   REAL DEFAULT 0.0,
    attend_personal_leave REAL DEFAULT 0.0,  -- 事假
    attend_sick_leave     REAL DEFAULT 0.0,  -- 病假
    attend_absent REAL DEFAULT 0.0,          -- 旷工
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(employee_id, year, month)
);
```

**设计原则**：
- 用 `employee_id` 关联 employees（注意：看 employees 表是用 `id` 还是 `employee_id` 做主键）
- 加 `(employee_id, year, month)` 联合唯一约束，支持按月 UPSERT
- 历史数据从 `salary_details` 迁移：INSERT INTO ... SELECT 方式

#### 第2步：后端路由

在 `main.py` 中新增：

```python
# ---- 考勤模块路由 ---- 

# 页面路由（HTML GET）
@app.get("/attendance")
@require_permission("attendance")  # ← 模块独立权限
async def attendance_page(request: Request):
    user = await require_login(request)
    now = datetime.now()
    sel_year = int(request.query_params.get("year", now.year))
    sel_month = int(request.query_params.get("month", now.month))
    
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        
        # 注意：employees 表 status 字段是中文 '在职' 不是 active=1
        cur = await db.execute(
            "SELECT id, employee_id, name, department FROM employees WHERE status='在职' ORDER BY department, name"
        )
        employees = await cur.fetchall()
        
        cur2 = await db.execute(
            "SELECT * FROM attendance_records WHERE year=? AND month=?",
            (sel_year, sel_month)
        )
        att_map = {r["employee_id"]: r for r in await cur2.fetchall()}

    # 组织数据：employee rows + attendance data
    records = []
    for emp in employees:
        att = att_map.get(emp["id"])
        records.append({
            "employee_id": emp["id"],
            "name": emp["name"],
            "department": emp["department"] or "",
            # attend fields from att or defaults
        })

    return HTMLResponse(render("attendance.html", request=request, ...))

# API 路由（数据操作）
@app.put("/api/attendance/records")
@require_permission("attendance")
async def save_attendance(data: AttendanceSave):
    user = await require_login(request)
    if user["role"] not in ("admin", "editor"):
        raise HTTPException(403, "仅管理员和编辑可操作")
    
    async with aiosqlite.connect(str(DB_PATH)) as db:
        for rec in data.records:
            await db.execute(
                """INSERT INTO attendance_records
                   (employee_id, year, month, attend_days, attend_personal, attend_sick)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(employee_id, year, month) DO UPDATE SET
                   attend_days=excluded.attend_days, ...""",
                (rec.employee_id, data.year, data.month, rec.attend_days, ...)
            )
        await db.commit()
    return {"ok": True, "saved": len(data.records)}
```

**Pydantic 模型示例**：
```python
class AttendanceRecord(BaseModel):
    employee_id: int
    attend_days: float = 22.0
    attend_personal: float = 0.0     # 事假
    attend_sick: float = 0.0          # 病假
    attend_late: float = 0.0
    attend_early: float = 0.0
    attend_absent: float = 0.0

class AttendanceSave(BaseModel):
    year: int
    month: int
    records: list[AttendanceRecord]
```

#### 第3步：前端模板 (`templates/{module}.html`)

典型结构：
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    {% include "head_common.html" ignore missing %}
    <title>考勤管理 — HRMS</title>
    <style>
        .attendance-table input[type="number"] { width: 70px; }
        .month-nav { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
    </style>
</head>
<body>
    {% include "navigation.html" ignore missing %}
    
    <div class="container">
        <h2>考勤管理</h2>
        
        <!-- 月份选择器 -->
        <div class="month-nav">
            <button onclick="goPrev()">‹</button>
            <select id="selYear" onchange="goTo()">...</select>年
            <select id="selMonth" onchange="goTo()">...</select>月
            <button onclick="goNext()">›</button>
            <button id="saveBtn" onclick="saveAttendance()" class="btn btn-primary">批量保存</button>
        </div>
        
        <!-- 员工考勤表格 -->
        <table id="attendance-table">
            <thead>
                <tr>
                    <th>姓名</th>
                    <th>部门</th>
                    <th>出勤<br/>天数</th>
                    <th>迟到</th>
                    <th>早退</th>
                    <th>事假</th>
                    <th>病假</th>
                    <th>旷工</th>
                </tr>
            </thead>
            <tbody>
                {% for rec in records %}
                <tr>
                    <td>{{ rec.name }}</td>
                    <td>{{ rec.department }}</td>
                    <td><input type="number" step="0.5" data-eid="{{ rec.employee_id }}" data-field="attend_days" value="{{ rec.attend_days }}"/></td>
                    ...
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    
    <script>
        function goPrev() { /* 月份-1 */ }
        function goNext() { /* 月份+1 */ }
        function goTo() { /* 跳转 */ }
        
        async function saveAttendance() {
            const records = [];
            document.querySelectorAll('[data-eid]').forEach(input => {
                const eid = parseInt(input.dataset.eid);
                const field = input.dataset.field;
                records[eid] = records[eid] || {employee_id: eid};
                records[eid][field] = parseFloat(input.value) || 0;
            });
            
            const res = await fetch('/api/attendance/records', {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    year: parseInt(document.getElementById('selYear').value),
                    month: parseInt(document.getElementById('selMonth').value),
                    records: Object.values(records)
                })
            });
            if (res.ok) toast('保存成功 ✅');
            else toast('保存失败', 'error');
        }
    </script>
</body>
</html>
```

#### 第4步：导航栏更新（所有模板）

在每个 HTML 模板的导航栏中插入新入口，**注意权限判断需要的变量**：

```html
<!-- 方式1：行内权限判断（适用于无 {% set %} 预定义的模板） -->
<a href="/attendance" class="btn btn-sm"
   {% if not ('"attendance"' in (current_user.permissions|default('[]')) or current_user.role == 'admin') %}
   style="display:none"
   {% endif %}>📋 考勤管理</a>

<!-- 方式2：预定义变量（适用于 index.html 等提前解析的模板） -->
{% set _perms = current_user.permissions | default('[]') %}
{% set _att = '"attendance"' in _perms or current_user.role == 'admin' %}
<a href="/attendance" class="btn btn-sm" {% if not _att %}style="display:none"{% endif %}>考勤</a>
```

需修改的模板文件列表（典型 5 个）：
- `index.html`（首页）
- `salary_list.html`（工资表列表）
- `salary_edit.html`（工资表编辑）
- `salary_basics.html`（薪酬参数）
- `admin_users.html`（用户管理 — 加复选框）

#### 第5步：用户管理加权限复选框

在 `admin_users.html` 的新增/编辑弹窗权限区域增加复选框，并同步 JS 中 saveUser/editUser/showAddModal 函数。

**三处必须修改**（缺一不可）：
1. HTML 复选框：`<label><input type="checkbox" id="permXxx" value="xxx"> XXX管理</label>`
2. `showAddModal()` 初始化：`document.getElementById('permXxx').checked = false;`
3. `editUser()` 读取权限：`document.getElementById('permXxx').checked = perms.includes('xxx');`
4. `saveUser()` 收集权限：`if (document.getElementById('permXxx').checked) checkedPerms.push('xxx');`

#### 验证清单

- [ ] 未登录访问 → 401/302
- [ ] 登录后页面渲染（200）+ 员工表格行
- [ ] 输入框 6 列 / 对应 data-field
- [ ] 月份切换按钮
- [ ] 批量保存 API（PUT）→ 200 `{"ok":true, "saved": N}`
- [ ] 页面重载后数据持久化
- [ ] 无权限用户访问 → 403
- [ ] 用户管理页新增权限复选框可用

### 考勤→工资联动

考勤数据保存时自动按 `salary_basics` 单价计算金额写入 `salary_details`。详细字段映射、参数 `item_key` 实际值、迟到字段名兼容处理、验证模式，详见 `references/attendance-salary-link.md`。

### 用工形式枚举（employment_type）

**后端验证允许的取值**（`validate_employment_type`）：
`在编`, `合同`, `劳务派遣`, `临聘`, `退休返聘`, `返聘`

**前端表单下拉框选项**（form.html）：
`在编`, `聘用`, `合同制`, `劳务派遣`, `临时`, `返聘`

**⚠️ 前后端枚举不一致**：后端用 `合同`/`临聘`，前端用 `合同制`/`临时`。当前能工作是因为前端提交的值被后端接受（前端值在后端 allowed 元组中有对应项），但长期应统一。

### 用工形式与工资模块的关系（2026-07-24 新增）

三种用工形式在工资模块中的处理方式不同：

| 用工形式 | 薪资标准 | 工资表 | 数据来源 | 社保/公积金 |
|----------|----------|--------|----------|-------------|
| 在编/聘用/合同制 | ✅ 有 | ✅ 有 | 从薪资标准自动生成 | 自动计算 |
| 返聘/临时 | ❌ 无 | ✅ 有 | 手填，默认取上个月数据 | **强制为 0** |
| 劳务派遣 | ❌ 无 | ❌ 无 | 工资由派遣公司发放 | 不适用 |

#### 返聘/临时员工工资表逻辑

**业务规则**：返聘和临时员工包含在工资表中，但工资数据手填，不关联薪资标准。新建工资表时，默认值取**上个月工资表数据**。

**实现细节**（`POST /api/salary/sheets` 新建工资表路由）：

1. 查询上个月工资表数据，按 `employee_id` 建立 `prev_map` 索引：
```python
prev_m = m - 1
prev_y = y
if prev_m == 0:
    prev_m = 12
    prev_y -= 1
cur = await db.execute(
    """SELECT sd.* FROM salary_details sd
       JOIN salary_sheets ss ON sd.sheet_id = ss.id
       WHERE ss.year=? AND ss.month=?""",
    (prev_y, prev_m)
)
prev_map = {row["employee_id"]: dict(row) async for row in cur}
```

2. 无薪资标准的员工（返聘/临时）：
   - **有上个月数据** → 复制 base_salary、各项补助、其他扣款到本月，社保/公积金强制为 0
   - **无上个月数据** → 全部字段为 0，`source='manual'`

3. 考勤/绩效字段始终从零开始（不继承上个月）

**薪资标准选择器**：`salary_standards` 页面新增员工时，排除返聘、临时、劳务派遣三类：
```sql
WHERE status != '离职' AND employment_type NOT IN ('劳务派遣', '返聘', '临时')
```

#### 劳务派遣员工不参与工资模块

**业务规则**：劳务派遣员工（`employment_type = '劳务派遣'`）的工资由派遣公司发放，不在 HRMS 工资系统中体现。

**受影响的 SQL 查询（3 处）**：

| 位置 | 功能 | 过滤条件 |
|------|------|---------|
| 薪资标准页员工选择器 | 新增薪资标准 | `WHERE status != '离职' AND employment_type NOT IN ('劳务派遣', '返聘', '临时')` |
| 新建工资表 | 生成月度工资表 | `WHERE e.status != '离职' AND e.employment_type != '劳务派遣'` |
| 考勤同步到工资 | 考勤写入工资明细 | `WHERE e.status='在职' AND e.employment_type != '劳务派遣'` |

**不受影响的页面**：员工管理列表页仍然显示所有非离职员工（需要管理他们的档案信息）。

**未来新增工资相关功能时**：任何查询在职员工用于工资/薪资/考勤计算的地方，都应考虑用工形式的过滤规则。

### ⚠️ 员工 ID 映射陷阱：`employee_id`（工号）≠ `id`（主键）

**问题**（2026-07-29）：考勤快速录入中，前端下拉框 `value` 使用了 `{{ e.employee_id }}`（工号字符串如 "002"），`parseInt("002")` = 2，但数据库外键 `attendance_records.employee_id` 引用的是 `employees.id`（自增主键，蔡旭凯的 id=11）。数据写入 `employee_id=2`，刷新后后端用 `emp["id"]=11` 查询 → 找不到记录 → **数据"消失"**。

**根因**：`employees` 表有两个 ID 字段，前端模板容易混淆：

| 字段 | 类型 | 用途 | 示例（蔡旭凯） |
|------|------|------|---------------|
| `id` | INTEGER PK AUTO | 数据库主键，**所有外键引用这个** | 11 |
| `employee_id` | TEXT UNIQUE | 员工工号/编码，**仅用于显示** | "002" |

**修复规则（所有 HRMS 前端模板）**：

```html
<!-- ❌ 错误：用了工号 -->
<option value="{{ e.employee_id }}">{{ e.name }}</option>

<!-- ✅ 正确：用了主键 -->
<option value="{{ e.id }}">{{ e.name }}</option>
```

**JS 端同样**：`empMap` 的 key 和 `allEmpIds` 收集都必须用 `e.id`，不能用 `e.employee_id`。

**影响范围**：任何前端下拉框、下拉选择、`<option value>`、`data-eid` 属性，只要值要传给后端 API 写入数据库，**必须用 `e.id`（主键整数）**。

**排查方法**：
```bash
# 查找数据库中 employee_id 不在 employees.id 中的孤儿记录
sqlite3 db/hrms.db "SELECT ar.employee_id FROM attendance_records ar WHERE ar.employee_id NOT IN (SELECT id FROM employees);"
```

**验证方法**：
```bash
# 对比前端选项 value 与数据库 id 是否一致
sqlite3 db/hrms.db "SELECT id, employee_id, name FROM employees WHERE id != CAST(employee_id AS INTEGER);"
```

### 考勤保存后汇总表格 DOM 不同步陷阱（2026-07-29 新增）

**现象**：用户在快速录入中填写缺勤数据，点击"保存"后 API 返回成功，数据库已写入，但切换到"汇总查看"→"缺勤统计"标签页时，表格中对应字段仍为 0。刷新页面后数据才出现。

**根因**：`saveAttendance()` 保存成功后只更新了 `originalData` 内存快照和 `renderCards()`（快速录入卡片），但**汇总查看模式的表格 DOM 是页面加载时后端 Jinja2 渲染的静态 HTML**，不会自动同步 `currentData` 中的新值。

**修复**（`attendance.html` 中新增 `syncTableValues()` 并在保存成功后调用）：

```javascript
// 同步汇总表格 input 值
function syncTableValues() {
    const inputs = document.querySelectorAll('.attendance-table input.inp-att');
    inputs.forEach(inp => {
        const row = inp.closest('tr');
        if (!row) return;
        const eid = parseInt(row.getAttribute('data-eid'));
        const field = inp.getAttribute('data-field');
        if (currentData[eid] && currentData[eid][field] !== undefined) {
            inp.value = currentData[eid][field];
        }
    });
}

// 在 saveAttendance 成功回调中调用：
if (data.ok) {
    showToast(`✅ 已保存 ${data.saved} 条考勤记录`, 'success');
    for (const eid of modified) {
        originalData[eid] = JSON.parse(JSON.stringify(currentData[eid]));
    }
    syncTableValues();  // ← 关键：同步汇总表格
    modified.clear();
    renderCards();
}
```

**设计原则**：当页面存在多个视图模式（快速录入卡片 + 汇总表格），且数据源为前端内存（`currentData`）而非重新请求后端时，**任何保存操作后都必须主动同步所有视图的 DOM**。

**排查思路**：当用户反馈"保存后数据不显示"时，按以下顺序排查：
1. 先查数据库确认数据是否写入（`SELECT ... FROM attendance_records WHERE employee_id=?`）
2. 如果数据库有数据但前端不显示 → 查 `const records` JS 变量（浏览器 DevTools Console 中执行 `records`）
3. 如果 `records` 有数据但表格 input 值为 0 → 问题在 DOM 同步逻辑，检查 `saveAttendance` 是否调用了同步函数
4. 如果 `records` 中数据为 0 → 问题在后端 `attendance_page` 路由的数据构建逻辑

### 已知陷阱

### 数据库字段存字符串 "None" 而非 SQL NULL

**现象**：页面显示 `"None"` 文字，Python 端 `if not value:` 判断失效。

**说明**：详见 `references/none-string-trap.md`。字段值可能是 Python 的字符串 `"None"`（来自 `str(None)` 写入），而非 SQL `NULL`。这会绕过空值判断和数据组合逻辑。修复方法：数据库层清理 + Python 层防御性清理双层保障。

- `employees.status` 是中文字段 `'在职'`，不是布尔值 `active=1`
- `employees` 表主键是 `id`，但员工编码是 `employee_id`（字符串）
- Jinja2 data-permissions 传递 JSON: 用 HTML data 属性，不用 onclick 参数（引号转义问题）
- 禁用用户的 editor 不能修改考勤：调用 PUT API 时需检查 role in ("admin", "editor")

### 首页每月操作入口

- 列表页增加「薪酬」菜单入口
- 薪酬首页显示各月工资表列表（年月、状态、总额、操作按钮）
- 当月未生成 → 显示「生成本月工资表」按钮
- 当月已生成 → 显示「编辑」「查看」「确认」按钮

## 实施指引

1. 数据库：新增独立表（如 `contracts`、`salary_standards`、`salary_sheets`、`salary_details`），关联 `employees.employee_id`
2. 后端路由：`/contracts/...`、`/salary/...` 独立路由组
3. 前端：独立页面，顶部导航栏加菜单入口
5. **权限：已实现模块级权限隔离（permissions JSON 数组）** — 详见 `references/module-permissions.md`
6. **子表操作后必须同步主表冗余字段**（如 contracts 新增后同步 employees.contract_type）

## 后端开发陷阱（2026-07-18 薪酬模块实战记录）

### venv Python 路径（2026-07-20 新增）

**问题**：HRMS 项目使用 `/home/bobobears/hrms/venv/` 虚拟环境安装依赖（aiosqlite, openpyxl 等），但直接执行 `python3 main.py` 用的是系统 Python（/usr/bin/python3），系统 Python 下 `import aiosqlite` 会 ModuleNotFoundError。

**症状**：进程启动后立刻崩溃，uvicorn 根本没监听端口。

**修复**：始终使用 venv Python：
```bash
# ❌ 错误
python3 main.py
# ✅ 正确
/home/bobobears/hrms/venv/bin/python3 main.py
```

**影响范围**：cron job 中的 DSA 分析、手动重启、Hermes background 进程启动，都需要注意使用 venv Python 路径。

详见 `references/route-not-registered-debugging.md`、`references/decimal-rounding.md` 获取路由注册失败和财务取整的详细记录。

### 模块导入失败 → 后续路由不注册（隐蔽）

当 `main.py` 顶部有 `from X import Y` 失败（ModuleNotFoundError），**该行之后的所有路由装饰器根本不执行**。uvicorn 启动时如果只关注端口是否监听（HTTP 200），容易以为 server 正常。

**症状**：新路由完全不存在于 OpenAPI 路由表中，旧路由（import 行之前的）正常工作。

**排查**：
```bash
# 1. 检查 OpenAPI 路由表
curl -s http://HOST:PORT/openapi.json | python3 -c "import sys,json; [print(p) for p in sorted(json.load(sys.stdin)['paths'])]" | grep "你的路由"
```

**修复**：补全缺失模块，或用 try/except ImportError 包裹可选导入。

**实际案例**（2026-07-20）：main.py 第 757 行的 from contract_templates.contracts_template import ... 因为 contract_templates/ 目录被删除而失败，导致第 757 行后的所有路由未注册。修复方法：重建 contract_templates/contracts_template.py 模块，提供 TEMPLATES 字典和 render_contract 函数的 stub 实现。不需要完整实现，能让 main.py 完整加载即可。

### aiosqlite row_factory 遗漏
每个 `async with aiosqlite.connect(...)` 块内部必须设置 `db.row_factory = aiosqlite.Row`。遗漏后 `fetchone()` 返回 tuple，`row["field_name"]` 会崩溃。创建类路由中尤其隐蔽——创建时通常不读明细，所以不查明细就发现不了。

### JOIN 列名覆盖
当两个表有同名字段（如 salary_details.status 和 salary_sheets.status），`aiosqlite.Row` 中后 SELECT 的覆盖先 SELECT 的。必须用 `SELECT s.status AS sheet_status` 显式起别名，代码中用 `row["sheet_status"]`。

### SQL UPDATE 拼写错误
手写 `UPDATE ... SET field=?` 时容易拼错列名（如 `total_gress` 而非 `total_gross`）。SQLite 返回 500 但错误信息被截断。预防：写完 SQL 后用 `grep -n "SET.*=" backend/main.py | grep salary` 检查，再用 `PRAGMA table_info` 验证。

### 首页列表渲染数据与编辑表单数据不一致的排查

...

### 员工删除/离职后关联模块未同步

**场景**：用户在员工管理页删除了员工（物理 DELETE），但工资表/考勤记录中仍有该员工的条目。或者标记为离职后，已存在的工资表没有自动移除该员工。

**根因**：

1. 员工管理页的「删除」操作是物理 `DELETE FROM employees`，不属于软删除。删除后 `salary_details.employee_id` 变为孤立引用
2. 标记离职（`status='离职'`）只影响**新建**工资表的自动过滤，已存在的工资表是创建时的快照，不会自动移除
3. `salary_details` 存的是员工编码（TEXT `'0020'`），不是 `employees.id`（INTEGER），员工被删除后无法通过 JOIN 找到姓名

**处理流程**（参考 `web-crud-application` skill 的 `references/employee-status-sync-after-leave.md`）：

1. 确认员工在 employees 表中的状态（在职/离职/已删除）
2. 查询哪些工资表包含该员工（`SELECT FROM salary_details WHERE employee_id=?`）
3. 从这些工资表中 DELETE 相应明细行
4. 重新统计每个工资表（SUM + COUNT → UPDATE salary_sheets）
5. 新建工资表自动过滤：已有 `WHERE e.status != '离职'` 条件

**预防方案**：员工管理应推荐「标记离职」而非物理删除。物理删除会导致工资表历史记录失去员工姓名关联，推荐在离职人员页面（`/archived`）提供永久删除功能。

**注意**：考勤模块（`attendance_records`）的清除流程与工资表类似——按 `employee_id` 删除该员工所有考勤记录。

当用户反馈"编辑页面已填写，但首页列表没显示"，按此顺序排查：

1. **检查首页路由的 SQL SELECT 字段列表** — 是否 SELECT 了该字段？（如 `gender` 在首页路由的 SELECT 列表中缺失，是最常见的原因）
2. **检查数据库实际字段名** — 编辑保存时使用的字段名（如 `admin_dept`/`tech_dept`）可能不同于首页渲染用的字段名（如 `department`）。用 `sqlite3 .schema employees` 确认所有字段。
3. **检查后端是否做了字段合并** — 员工编辑页可能有多个细分字段（行政管理/技术管理），首页需要做合并逻辑。如果首页只是简单取 `department`，而数据填在了 `admin_dept`/`tech_dept`，就出现"编辑有、首页无"的现象。
4. **检查数据库数据是否存在** — 用 `SELECT employee_id, name, 字段名 FROM employees WHERE 字段名 IS NOT NULL AND 字段名 != ''` 确认数据确实存在。
5. **检查 Jinja2 模板中的字段引用** — 模板中引用的字段名必须与 Python dict 中的 key 一致。

**典型场景**：首页只查 `department`/`position`，但编辑表单将部门/岗位存到了 `admin_dept`/`admin_position`/`tech_dept`/`tech_position`。修复方式：在首页路由中做字段组合（优先取 `department`，为空时从 `admin_*`+`tech_*` 组合）。

### 工资表编辑页修改后界面数字不更新的 DOM 陷阱

**现象**：用户在工资表编辑页修改基本工资（如 2800 → 1450），弹窗输入框确认后，后端 API 返回成功，数据库已更新，但**表格中该单元格的显示数字不变**。刷新页面后才看到新值。

**根因**：`salary_edit.html` 中基本工资单元格的值是一个裸文本节点（`{{ '%.2f'|format(d.base_salary) }}`），而非带 `id` 的 `<span>` 元素。`updateCell()` 函数中的 `document.getElementById('base-{detailId}')` 找不到目标，导致前端 DOM 更新静默失败。

**修复**（两处同时改）：

1. **HTML 模板** — 给基本工资值加 `<span id>` 包裹：
```html
<!-- 修复前 -->
<td class="amount cell-editable col-basic" onclick="openPopover(event,'basic-{{ d.id }}')">
    {{ '%.2f'|format(d.base_salary) }}
    <div id="basic-{{ d.id }}" class="popover">...</div>
</td>

<!-- 修复后 -->
<td class="amount cell-editable col-basic" onclick="openPopover(event,'basic-{{ d.id }}')">
    <span id="base-{{ d.id }}">{{ '%.2f'|format(d.base_salary) }}</span>
    <div id="basic-{{ d.id }}" class="popover">...</div>
</td>
```

2. **JS updateCell 函数** — 添加 DOM 更新逻辑（在更新汇总列之后）：
```javascript
// updateCell 函数中，在更新 gross/deduct/net 之后添加：
const baseEl = document.getElementById(`base-${detailId}`);
if (baseEl) baseEl.textContent = d.base_salary.toFixed(2);
```

**验证方法**：修改后重启 uvicorn，编辑基本工资 → 确认 → 观察表格数字是否立即变化。同时检查数据库 `salary_details.base_salary` 是否已更新。

**排查思路**：当用户反馈"改了但界面没变"时，先查数据库确认数据是否写入（`SELECT base_salary FROM salary_details WHERE id=?`）。如果数据库已更新但界面没变，问题在前端 DOM 更新逻辑，而非后端 API。

### 工资表编辑页"其他扣款/补助"子项功能空壳陷阱（2026-07-28 新增）

**现象**：用户在扣发/补助弹窗中点击"+"添加其他扣款/补助子项，**没有任何反应**。后端的 `deduct_other` 和 `deduct_other_json` 字段始终为 `0.0` / `[]`。已有的子项在弹窗中也**不显示**。

**根因**：`salary_edit.html` 中 `renderOtherItems()` 函数直接 `return`（空函数），`addOtherItem()` 只有 GET 请求没有 PUT 更新。这两个函数在初始开发时作为占位符存在，但从未被实现。后端 `_recalc_detail()` 计算逻辑是正确的，问题**纯前端**。

**修复**（`salary_edit.html` 中三个函数）：

1. **`renderOtherItems(detailId, field, jsonStr)`** — 解析 JSON 字符串，渲染子项列表（含删除按钮）
2. **`addOtherItem(detailId, field)`** — GET 当前数据 → 追加子项 → PUT 同时更新 `*_json`（子项列表）和 `*`（合计金额）
3. **`deleteOtherItem(detailId, field, idx)`** — 删除子项并重新计算合计
4. **页面加载时自动渲染** — `DOMContentLoaded` 遍历所有 `<tr>`，fetch 每条明细的 `allow_other_json` 和 `deduct_other_json`，调用 `renderOtherItems`

**关键设计原则**：
- 同时更新 `*_json`（子项列表）和 `*`（合计金额），后端 `_recalc_detail()` 依赖合计值
- 添加/删除后必须更新：①汇总列（totalDeduct/net）②组小计（deduct-total/allow-total span）③子项列表 DOM ④工资表汇总栏（refreshSummary）
- "其他补助"和"其他扣款"共享同一套函数，通过 `field` 参数区分

**排查思路**：当用户反馈"其他扣款没纳入统计"时，先查数据库 `deduct_other` 和 `deduct_other_json` 字段——如果都是 0/[]，问题在前端添加功能未实现；如果有值但 total_deduct 不对，问题在后端 `_recalc_detail()` 计算逻辑。

### salary_basics 页面分类枚举是硬编码的陷阱

`salary_basics.html` 模板中的 `categories` 字典和 `cat_order` 数组是**硬编码**的，只定义了新增时的分类。

**症状**：数据库中已有数据，页面只显示部分分类，不显示的分类对应参数完全不可见。

**排查**：对比数据库中的 DISTINCT category 与模板中的 categories 字典 key。

```sql
SELECT DISTINCT category FROM salary_basics;
```

**修复**：在 `salary_basics.html` 的 `categories` 字典和 `cat_order` 中同步添加新的分类键值对。每个新分类需要：
- 一个字典条目（label, icon）
- cat_order 数组中的位置

**典型场景**（2026-07-21）：增加了 `allowance_level_admin`、`allowance_level_position`、`allowance_level_skill`、`allowance_level_seniority` 四个分类（共27条等级参数），但模板未同步添加 → 页面只显示6个旧分类。

**反向场景**（删除分类时也要同步模板）：删除 `allowance` 分类的6条记录后，忘记从 `categories` 字典中移除 → 页面显示一个空的"补助参考值"分类（无参数，count=0）。修复：同时删除字典条目和 `cat_order` 中的引用。

### 工资表新建后数据全为 0 的排查（2026-07-27 更新）

**现象**: 新建工资表后，所有数据仍是 0.0。

**根因（旧）**：`salary_standards` 表为空（该表已于 2026-07-25 删除，此根因不再适用）。

**根因（新）**：
1. `salary_basics` 表中 `base_min` 值为 0 → 基本工资全为 0
2. `salary_basics` 中补助等级参数为空或缺失 → 四项补助全为 0
3. 员工档案中 `admin_level`/`qualification`/`tech_position` 为空 → 等级匹配失败

**排查步骤**:
```bash
# 1. 检查 salary_basics 基本工资
sqlite3 db/hrms.db "SELECT item_key, item_value FROM salary_basics WHERE item_key='base_min'"

# 2. 检查补助等级参数
sqlite3 db/hrms.db "SELECT category, item_key, item_value FROM salary_basics WHERE category LIKE 'allowance_level%'"

# 3. 检查员工档案字段是否填写
sqlite3 db/hrms.db "SELECT employee_id, name, admin_level, qualification, tech_position FROM employees LIMIT 5"
```

**修复**:
1. 在「薪酬参数」页面（`/salary/basics`）设置基本工资和补助等级参数
2. 在员工档案中填写行政级别、职称、技术职务
3. 重新新建工资表或点击"重新同步"

#### ⚠️ 社保/公积金比例单位陷阱 + round() 银行家舍入

`salary_standards.social_rate` 和 `housing_fund_rate` 存的是**百分比值**（10.5 表示 10.5%，8.0 表示 8%）。计算扣款时**必须除以100**：

```python
# ❌ 错误1：4311 × 10.5 = 45265.50（没除以100）
round(social_base * social_rate, 2)

# ❌ 错误2：round 使用银行家舍入，452.655 → 452.65
round(social_base * social_rate / 100, 2)

# ✅ 正确：Decimal 四舍五入，4311 × 10.5 / 100 = 452.66
from decimal import Decimal, ROUND_HALF_UP
float(Decimal(str(social_base * social_rate / 100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
```

**Python `round()` 的银行家舍入陷阱**：`round(452.655, 2)` 返回 `452.65` 而非 `452.66`，因为 Python 3 使用**四舍六入五成双**（banker's rounding）。涉及财务计算时必须用 `Decimal + ROUND_HALF_UP`。

**推荐做法**：在文件顶层定义辅助函数统一使用：

```python
def _r2(v: float) -> float:
    """四舍五入到两位小数（替代 round，避免银行家舍入）"""
    from decimal import Decimal, ROUND_HALF_UP
    return float(Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
```

此陷阱存在于两处代码：

```python
# ❌ 错误：4311 × 10.5 = 45265.50  ❌
round(social_base * social_rate, 2)

# ✅ 正确：4311 × 10.5 / 100 = 452.66  ✅
round(social_base * social_rate / 100, 2)
```

此陷阱存在于两处代码：
1. 新建工资表路由 `POST /api/salary/sheets`
2. 从标准同步路由 `POST /api/salary/sheets/{id}/sync-standard`

两处的 `deduct_social` 和 `deduct_housing` 计算都需要 `/ 100`。

**验证方法**：新建工资表后检查 `deduct_social` 值。
- 社保基数4311 × 三险合计10.5% = 452.66 → ✅ 正确
- 如果看到45265 → ❌ 没除以100

**修复**:
1. 在「薪酬参数」页面（`/salary/basics`）设置基本工资和补助等级参数
2. 在员工档案中填写行政级别、职称、技术职务
3. 重新新建工资表或点击"重新同步"

**注意**: 这是正常的设计，不是 bug——工资表创建时是**一次拍照复制**，后续薪酬参数变化不会自动推送到已存在的工资表。用户修改参数后需手动点击"重新同步"按钮更新当前工资表。

### 公积金基数从上下限改为按行政等级分档

**设计**（2026-07-21 实现）：

原方案使用 `fund_base_min` / `fund_base_max` 上下限框架。改为按行政等级固定基数：

| 行政等级 | 公积金基数 |
|---------|-----------|
| 正职    | 7,500 元  |
| 副职    | 5,000 元  |
| 主管    | 3,750 元  |
| 主办    | 3,125 元  |
| 无级别   | 2,500 元  |

**实现**：删除旧 `fund_base_min`/`fund_base_max`，新增5条 `fund_admin_*` 参数（fund_admin_director/vice/supervisor/chargeman/general），均在 `salary_basics` 表中 `category='housing_fund'`。**每条可手动调整**（非自动计算），保留行内编辑功能。

**后台计算逻辑**：工资表计算时，根据员工 `admin_level` 字段匹配对应的 `fund_admin_*` 基数，如：
```python
admin_to_fund_key = {
    '正职': 'fund_admin_director', '副职': 'fund_admin_vice',
    '主管': 'fund_admin_supervisor', '主办': 'fund_admin_chargeman',
    '': 'fund_admin_general'
}  # None/空映射到无级别
```

### 自动计算/只读字段在 salary_basics 页面的显示模式

对于由公式自动计算、不允许手动编辑的参数（如事假/病假扣款 `deduct_absent_day`、`deduct_sick_day`），需在模板中做特殊处理：

1. **不显示数字** — 用 `<span class="val-display" style="color:var(--text-secondary);font-weight:400;font-style:italic">自动计算</span>` 代替 `{{ '%.2f' | format(item.item_value) }}`
2. **不可点击编辑** — 移除 `onclick="editValue(this)"`，改为 `title="由公式自动计算"`
3. **显示公式说明** — 在 `description` 字段中存储公式，模板中通过 `{{ item.description }}` 显示

**模板模式**：
```jinja2
{% if item.item_key in ('deduct_absent_day', 'deduct_sick_day') %}
<div class="param-value" title="由公式自动计算">
    <span class="val-display" style="color:var(--text-secondary);font-weight:400;font-style:italic">自动计算</span>
</div>
{% else %}
<div class="param-value" onclick="editValue(this)" title="点击修改">
    <span class="val-display">{{ '%.2f' | format(item.item_value) }}</span>
</div>
{% endif %}
```

**注意**：这类特殊处理的参数不应在 description 为空时留空，应填入公式文字说明。数据库中的 `item_value` 保留0.0作为占位。

