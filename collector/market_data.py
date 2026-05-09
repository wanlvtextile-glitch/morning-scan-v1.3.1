# 市场行情自动采集
# fetch_a_stock_indices(last_trading_date) -> dict | None   A股三大指数昨收
# fetch_us_market_data(us_market_date)    -> list | None   美股关键标的日收（无走强走弱评判）
#
# 被谁调用：editorial_layer/market_context.py

import logging
from datetime import date as _date, timedelta as _td
from typing import Optional

logger = logging.getLogger(__name__)

# A股三大指数
_A_INDEX_MAP = [
    ('sh000001', '上证指数'),
    ('sz399001', '深证成指'),
    ('sz399006', '创业板指'),
]

# 美股监控列表：(akshare symbol, display name, description, type)
# type: index / etf / stock
_US_SYMBOLS = [
    ('.IXIC',    'NASDAQ', '纳斯达克综合',    'index'),
    ('.INX',     'S&P500', '标普500',          'index'),
    ('.DJI',     'DJI',    '道琼斯',           'index'),
    ('105.QQQ',  'QQQ',    '纳斯达克100 ETF',  'etf'),
    ('105.SOXX', 'SOXX',   '费城半导体 ETF',   'etf'),
    ('105.NVDA', 'NVDA',   '英伟达',           'stock'),
    ('105.AMD',  'AMD',    'AMD',              'stock'),
    ('106.TSM',  'TSM',    '台积电 ADR',       'stock'),
]


def _get_ak():
    try:
        import akshare as ak
        return ak
    except ImportError:
        logger.warning('akshare 未安装，市场数据采集不可用')
        return None


def fetch_a_stock_indices(last_trading_date: str) -> Optional[dict]:
    """
    采集 A 股三大指数在 last_trading_date 的收盘数据。

    返回格式：
    {
        '上证指数': {'price': 4180.09, 'change_pct': '+0.48%', 'date': '2026-05-07'},
        '深证成指': {...},
        '创业板指': {...},
    }
    任意一条失败只跳过该条，全部失败返回 None。
    """
    ak = _get_ak()
    if ak is None:
        return None

    result = {}
    for symbol, name in _A_INDEX_MAP:
        try:
            df = ak.stock_zh_index_daily(symbol=symbol)
            if df is None or df.empty:
                logger.warning('%s 无数据', name)
                continue

            df = df.sort_values('date').reset_index(drop=True)
            df['date'] = df['date'].astype(str)

            if last_trading_date:
                mask = df['date'] == last_trading_date
                positions = df[mask].index.tolist()
            else:
                positions = []

            if positions:
                pos = positions[0]
                actual_date = last_trading_date
            else:
                pos = len(df) - 1
                actual_date = str(df.iloc[pos]['date'])
                if last_trading_date:
                    logger.info('%s: 未找到 %s，使用最新数据 %s', name, last_trading_date, actual_date)

            close = float(df.iloc[pos]['close'])

            if pos > 0:
                prev_close = float(df.iloc[pos - 1]['close'])
                pct = (close - prev_close) / prev_close * 100
                change_pct_str = f'{pct:+.2f}%'
            else:
                change_pct_str = 'N/A'

            result[name] = {
                'price':      round(close, 2),
                'change_pct': change_pct_str,
                'date':       actual_date,
            }
        except Exception as exc:
            logger.warning('%s 采集失败: %s', name, exc)

    return result if result else None


def fetch_us_market_data(us_market_date: str) -> Optional[list]:
    """
    采集美股关键标的收盘数据（结构化列表，无走强走弱评判）。

    返回格式：
    [
        {'symbol': 'NASDAQ', 'name': '纳斯达克综合', 'price': 25806.20,
         'change_pct': '-0.13%', 'date': '2026-05-07', 'type': 'index'},
        ...
    ]
    全部失败返回 None。
    """
    ak = _get_ak()
    if ak is None:
        return None

    result = []

    # ── 主要指数（index_us_stock_sina：.IXIC / .INX / .DJI）──────────
    for sym, display, desc, stype in _US_SYMBOLS:
        if stype != 'index':
            continue
        try:
            df = ak.index_us_stock_sina(symbol=sym)
            if df is None or df.empty:
                continue

            df = df.sort_values('date').reset_index(drop=True)
            df['date'] = df['date'].astype(str)

            if us_market_date:
                mask = df['date'] == us_market_date
                positions = df[mask].index.tolist()
            else:
                positions = []

            if positions:
                pos = positions[0]
                actual_date = us_market_date
            else:
                pos = len(df) - 1
                actual_date = str(df.iloc[pos]['date'])
                if us_market_date:
                    logger.info('%s: 未找到 %s，使用最新数据 %s', display, us_market_date, actual_date)

            close = float(df.iloc[pos]['close'])

            if pos > 0:
                prev_close = float(df.iloc[pos - 1]['close'])
                pct = (close - prev_close) / prev_close * 100
                change_pct_str = f'{pct:+.2f}%'
            else:
                change_pct_str = 'N/A'

            result.append({
                'symbol':     display,
                'name':       desc,
                'price':      round(close, 2),
                'change_pct': change_pct_str,
                'date':       actual_date,
                'type':       stype,
            })
        except Exception as exc:
            logger.warning('美股指数 %s 采集失败: %s', display, exc)
            print(f'[市场数据] 美股指数 {display} 采集失败（可能为代理限制，不影响 A 股报告）：{type(exc).__name__}')

    # ── ETF + 个股（stock_us_hist：change_pct 由 API 直接提供）──────
    if us_market_date:
        try:
            target_dt = _date.fromisoformat(us_market_date)
        except ValueError:
            target_dt = _date.today() - _td(days=1)
    else:
        target_dt = _date.today() - _td(days=1)

    start_str = (target_dt - _td(days=7)).strftime('%Y%m%d')
    end_str = target_dt.strftime('%Y%m%d')

    for sym, display, desc, stype in _US_SYMBOLS:
        if stype not in ('etf', 'stock'):
            continue
        try:
            df = ak.stock_us_hist(symbol=sym, period='daily',
                                  start_date=start_str, end_date=end_str, adjust='')
            if df is None or df.empty:
                logger.info('%s (%s): 无数据', display, sym)
                continue

            # 列位置（API 返回列名为乱码，固定顺序）：
            # 0=日期 1=开盘 2=收盘 3=最高 4=最低 5=成交量 6=成交额 7=振幅 8=涨跌幅 9=涨跌额 10=换手率
            r = df.iloc[-1]
            date_val    = str(r.iloc[0])
            close       = float(r.iloc[2])
            change_pct_val = float(r.iloc[8])

            result.append({
                'symbol':     display,
                'name':       desc,
                'price':      round(close, 2),
                'change_pct': f'{change_pct_val:+.2f}%',
                'date':       date_val,
                'type':       stype,
            })
        except Exception as exc:
            logger.warning('美股 %s (%s) 采集失败: %s', display, sym, exc)
            print(f'[市场数据] 美股 {display}({sym}) 采集失败（可能为代理限制）：{type(exc).__name__}')

    return result if result else None
