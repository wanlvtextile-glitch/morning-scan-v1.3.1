# 时间窗口规则层
# 负责计算本次采集应覆盖的时段。
# 规则：上一个 A 股交易日 15:00 → 今日 09:00
# 使用 chinese_calendar 判断节假日和调休，覆盖五一、春节等长假。
# 上限保护：连续长假后窗口最长不超过 MAX_WINDOW_DAYS 天，防止采集量过大。

from datetime import datetime, timedelta, date, timezone
from chinese_calendar import is_holiday

MAX_WINDOW_DAYS = 5  # 窗口最长天数（春节/五一等长假后生效）
CHINA_TZ = timezone(timedelta(hours=8))


def is_trading_day(d: date) -> bool:
    """判断某日是否为 A 股交易日（周一至周五且非节假日）"""
    # 调休上班的周末（如某些周六）仍不开盘，weekday() 已涵盖
    return d.weekday() < 5 and not is_holiday(d)


def get_previous_trading_day(reference_date: date) -> date:
    """返回 reference_date 前最近的一个交易日"""
    day = reference_date - timedelta(days=1)
    while not is_trading_day(day):
        day -= timedelta(days=1)
    return day


def get_time_window():
    """
    返回本次采集的时间窗口 (start, end)。
    start = 上一个交易日 15:00（不早于 today - MAX_WINDOW_DAYS 零点）
    end   = 今日 09:00
    """
    today = date.today()
    end   = datetime.combine(today, datetime.min.time().replace(hour=9), tzinfo=CHINA_TZ)
    prev  = get_previous_trading_day(today)
    start = datetime.combine(prev, datetime.min.time().replace(hour=15), tzinfo=CHINA_TZ)

    # 上限保护：长假后窗口超过 MAX_WINDOW_DAYS 天时截断
    earliest_allowed = datetime.combine(
        today - timedelta(days=MAX_WINDOW_DAYS), datetime.min.time(), tzinfo=CHINA_TZ
    )
    if start < earliest_allowed:
        start = earliest_allowed

    return start, end
