# 从标准同步到工资表（sync-standard 实现）

## 架构变更（2026-07-25）

`salary_standards` 表已被移除。sync-standard 不再读写该中间层，而是直接从 `employees` 属性字段 + `salary_basics` 等级表实时计算所有补助和扣款数据。

## 场景

用户在员工档案中修改了 qualification/admin_level/tech_position/hire_date，或在薪酬参数中修改了等级金额后，希望已存在的工资表同步更新。

## 业务规则

- 仅 `draft` 状态的工资表可同步
- 同步覆盖范围：
  - **四项补助**：从 `calc_employee_allowances(eid, db)` **重新计算**（根据员工档案 + salary_basics）
  - **基本工资**：从 salary_basics `base_min` 取值
  - **社保/公积金扣款**：从 salary_basics 参数表取值（基数下限、按 admin_level 分档的公积金基数）
- 不覆盖范围：考勤4项、绩效2项、考勤扣发、其他扣款（这些是每月手动填写的）
- 无薪资标准的员工（返聘/临时）→ 补助/社保公积金重置为0
- 同步后自动重算应发/实发，页面reload

## 后端代码逻辑（main.py）

```python
# 遍历明细中每位员工
for eid in eids:
    # 直接从员工档案 + salary_basics 重新计算四项补助
    auto = await calc_employee_allowances(eid, db)

    # 基本工资从 salary_basics 取
    base_min = await _get_salary_basics_value(db, 'base_salary', 'base_min')

    # 社保/公积金从 salary_basics 取
    social_base = await _get_salary_basics_value(db, 'social_security', 'ss_base_lower')
    social_rate = await _get_salary_basics_rates(db, 'social_security')  # pension + medical + unemploy
    housing_base = await _get_hf_base_for_level(db, admin_level)
    housing_rate = await _get_salary_basics_value(db, 'housing_fund', 'hf_employee_rate')

    detail = {
        "base_salary": base_min,
        "allow_admin": auto["allow_admin"],
        "allow_position": auto["allow_position"],
        "allow_skill": auto["allow_skill"],
        "allow_seniority": auto["allow_seniority"],
        "allow_special": 0,  # 不再从 salary_standards 读取
        "allow_other": 0,
        "deduct_social": _r2(social_base * social_rate / 100),
        "deduct_housing": _r2(housing_base * housing_rate / 100),
    }
```

## 依赖函数

- `calc_employee_allowances(employee_id, db)` — 读取员工档案四字段，从 salary_basics 匹配等级值
- `_load_allowance_levels(db)` — 加载所有等级映射（admin/position/skill/seniority）
- `_r2(v)` — `Decimal` 四舍五入到两位小数（避免 `round()` 银行家舍入）

## 典型调试：技能等级变更后工资表未更新

**症状**：员工档案中 `qualification` 改为"中级"，sync-standard 后工资表 `allow_skill` 仍为旧值

**排查顺序**：
1. 确认 `employees.qualification` 已更新 → ✅
2. 确认 `_load_allowance_levels` 加载的 `levels["skill"]` 包含"中级"键 → ✅
3. 确认 `calc_employee_allowances` 对"中级"返回 400 → ✅
4. 确认 `sync-standard` 循环中调用了 `calc_employee_allowances` → ✅（架构变更后直接调用）
