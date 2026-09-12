#!/usr/bin/env python3
"""
检查今天是否是 A 股交易日。
返回 0 = 是交易日，1 = 非交易日（周末或节假日）。

做定时任务前置检查用，避免非交易日浪费 API 调用。
"""
import sys
from datetime import date, datetime

# 2026年中国A股法定节假日（不含周末）
# 元旦: 1/1 (周四)
# 春节: 2/17-2/23 (周二-周日)
# 清明节: 4/4-4/5 (周六-周日) -> 4/6(周一)补休
# 劳动节: 5/1 (周五)
# 端午节: 6/19 (周五)
# 中秋节+国庆节: 9/27-10/4
HOLIDAYS_2026 = {
    "2026-01-01",  # 元旦
    # 春节 2/17-2/23 (周二至周日，其中2/21-22周末，实际放假2/17-2/23)
    "2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20",
    "2026-02-21", "2026-02-22", "2026-02-23",
    # 清明节补休 4/6
    "2026-04-06",
    # 劳动节 5/1
    "2026-05-01",
    # 端午节 6/19
    "2026-06-19",
    # 中秋节+国庆节 9/27-10/4
    "2026-09-27", "2026-09-28", "2026-09-29", "2026-09-30",
    "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04",
}

# 调休上班日（周末补班）
WORKDAYS_2026 = {
    "2026-02-15",   # 周日→春节补班
    "2026-02-28",   # 周六→春节补班
    "2026-09-26",   # 周六→国庆补班
}


def is_trading_day(check_date=None):
    """判断是否A股交易日：周一至周五，扣除法定节假日，加上调休上班日"""
    if check_date is None:
        check_date = date.today()
    
    date_str = check_date.isoformat()
    weekday = check_date.weekday()  # 0=周一, 6=周日
    
    # 调休上班日
    if date_str in WORKDAYS_2026:
        return True
    
    # 法定节假日
    if date_str in HOLIDAYS_2026:
        return False
    
    # 周末
    if weekday >= 5:
        return False
    
    return True


if __name__ == "__main__":
    today = date.today()
    if is_trading_day(today):
        print(f"✅ {today} 是交易日")
        sys.exit(0)
    else:
        print(f"⏭️ {today} 非交易日，跳过")
        sys.exit(1)
