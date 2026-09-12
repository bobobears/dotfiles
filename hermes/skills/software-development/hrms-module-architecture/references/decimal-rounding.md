# 财务金额取整：Decimal vs Python round()

## 问题

Python 3 的 `round()` 使用**银行家舍入法**（Banker's Rounding / 四舍六入五成双）：

- `round(452.655, 2)` → **452.65**（期望 452.66）
- 因为 452.655 的小数第三位是 5，银行家舍入向偶数方向舍

这在财务计算中不可接受——中国会计准则要求四舍五入。

## 解决方案

使用 `Decimal` + `ROUND_HALF_UP`：

```python
from decimal import Decimal, ROUND_HALF_UP

def _r2(v: float) -> float:
    """四舍五入到两位小数"""
    return float(Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
```

关键点：
- `Decimal(str(v))` — 用字符串构造 Decimal，避免浮点数二进制表示失真
- `.quantize(Decimal("0.01"))` — 精确定位到两位小数
- `rounding=ROUND_HALF_UP` — 四舍五入

## 验证

```python
_r2(452.655)  # → 452.66 ✅
_r2(452.654)  # → 452.65 ✅
_r2(4311 * 10.5 / 100)  # = _r2(452.655) → 452.66 ✅
_r2(2500 * 8.0 / 100)   # = _r2(200.0) → 200.00 ✅
```

## 在 HRMS 中的使用位置

两处计算社保/公积金扣款的地方都用了 `_r2()`：

1. **新建工资表**：`POST /api/salary/sheets`
2. **从标准同步**：`POST /api/salary/sheets/{id}/sync-standard`

```python
detail = {
    ...
    "deduct_social": _r2(std["social_base"] * std["social_rate"] / 100),
    "deduct_housing": _r2(std["housing_fund_base"] * std["housing_fund_rate"] / 100),
}
```

## 关于比例字段的单位

`salary_standards.social_rate` 和 `housing_fund_rate` 存的是**百分比值**：
- `10.5` 表示 10.5%
- `8.0` 表示 8%

计算时必须**除以 100**：`social_base * social_rate / 100`

如果不除以 100 → 社保扣款变成 `4311 × 10.5 = 45265.50`（3倍月薪），这是错误的。
