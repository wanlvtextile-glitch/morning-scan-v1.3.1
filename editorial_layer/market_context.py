# 编辑层：市场背景结构构建
# Python 自动填充 scan_date / last_trading_date / us_market_date / dedup_stats /
#   indices（akshare A股三大指数）/ us_markets（akshare/yfinance 美股关键标的列表）。
# websearch_supplement 仍留给 Claude（hotrank_only 专项）。
# 被谁调用：editorial_layer/entry.py

from datetime import date as _date, timedelta as _timedelta


def _prev_us_trading_day(scan_date_str: str) -> str:
    """返回 scan_date 前一个美股交易日（仅排除美股周末）的 YYYY-MM-DD 字符串。
    周一 → 上周五（-3天）；其余工作日 → 前一天（-1天）。
    """
    try:
        d = _date.fromisoformat(scan_date_str)
    except Exception:
        return ''
    delta = 3 if d.weekday() == 0 else 1
    return (d - _timedelta(days=delta)).isoformat()


def build_market_context(context: dict) -> dict:
    """
    构建市场背景结构对象。

    Python 自动填充：
      scan_date         - 扫描日期（今日）
      last_trading_date - A 股上一个实际交易日
      us_market_date    - 隔夜美股日期（scan_date 前一个美股交易日，周一→上周五）
      dedup_stats       - 去重统计
      confidence        - 置信度
      indices           - A 股三大指数昨收（akshare；失败时为 None）
      us_markets        - 美股关键标的列表（akshare；失败时为 None；无走强走弱评判）

    Claude 填充（值为 None 时为占位）：
      websearch_supplement - WebSearch 补充摘要文本（hotrank_only 专项）
    """
    from collector.market_data import fetch_a_stock_indices, fetch_us_market_data

    tws = context.get('time_window_start', '')
    last_trading_date = tws[:10] if tws else ''

    scan_date      = context.get('date', '')
    us_market_date = _prev_us_trading_day(scan_date)

    indices    = fetch_a_stock_indices(last_trading_date)
    us_markets = fetch_us_market_data(us_market_date)

    return {
        'scan_date':             scan_date,
        'last_trading_date':     last_trading_date,
        'us_market_date':        us_market_date,
        'confidence':            context.get('confidence', 'unknown'),
        'dedup_stats':           context.get('dedup_stats', {}),
        'indices':               indices,     # dict | None
        'us_markets':            us_markets,  # list | None（无走强走弱评判）
        'websearch_supplement':  None,        # Claude 填充：hotrank_only 专项摘要
    }
