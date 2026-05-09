# 各来源抓取层
# 包含四个主源抓取函数 + 一个补充源接收函数：
#   scrape_taoguba         → 淘股吧热帖（论坛热帖，分页抓取）
#   scrape_ths_news        → 同花顺早报（JS 文件解析，GBK 编码）
#   scrape_ths_hotrank     → 同花顺人气榜（HTML 表格解析）
#   scrape_xueqiu          → 雪球热帖（JSON API，需 Cookie）
#   make_websearch_result  → WebSearch 补充源（由 Claude 执行后注入，非 Python 直抓）
#
# 每个函数均返回 SourceResult，不抛异常，失败信息写入 error_type。

import os
import json as _json
import time as _time
from datetime import datetime
from bs4 import BeautifulSoup
import requests as _requests

from collector.models import NewsItem, SourceResult
from collector.http_client import HEADERS, SOURCE_BUDGET, REQUEST_TIMEOUT, fetch_with_retry


# ── 淘股吧 ────────────────────────────────────────────────────────────────────
# 原域名 taoguba.com.cn 已迁移至 tgb.cn，使用 newIndex API 获取热帖列表
# getNowRecommend 按时间整体倒序（每页覆盖约 1~2 小时），但夹杂少量热门旧帖；
# totalPageNum 返回值约 5000（全库），不可用于判断末页；
# 早退条件：连续 2 页中所有帖子均早于 start（window boundary confirmed）。

TAOGUBA_API_URL     = 'https://www.tgb.cn/newIndex/getNowRecommend'
TAOGUBA_ARTICLE_URL = 'https://www.tgb.cn/Article/showArticle?topicID='
TAOGUBA_MAX_PAGES   = 20  # 约 5 页覆盖 18h 窗口，最多翻 20 页保证完整性

TAOGUBA_HEADERS = {
    **HEADERS,
    'Referer': 'https://www.tgb.cn/hot',
    'X-Requested-With': 'XMLHttpRequest',
    'Accept': 'application/json, text/plain, */*',
}


def scrape_taoguba(start: datetime, end: datetime) -> SourceResult:
    """抓取淘股吧热帖，按时间窗口过滤。
    接口时间整体倒序，但夹杂热门旧帖；用连续 2 页全部早于 start 作为早退条件。
    """
    budget_start         = _time.time()
    items                = []
    consecutive_all_old  = 0  # 连续"全部早于 start"的页数计数

    for page in range(1, TAOGUBA_MAX_PAGES + 1):
        if _time.time() - budget_start > SOURCE_BUDGET:
            break

        resp = fetch_with_retry(TAOGUBA_API_URL,
                                params={'pageNo': page},
                                headers=TAOGUBA_HEADERS)
        if resp is None:
            if page == 1:
                return SourceResult('淘股吧', True, False, [],
                                    error_type='fetch_failed')
            break

        try:
            data = resp.json()
        except Exception:
            if page == 1:
                return SourceResult('淘股吧', True, False, [],
                                    error_type='parse_failed')
            break

        dto        = data.get('dto', {})
        page_items = dto.get('list', [])
        if not page_items:
            break

        page_all_old = True
        for post in page_items:
            ts_ms = post.get('dateTime', 0)
            if not ts_ms:
                continue
            pub = datetime.fromtimestamp(ts_ms / 1000)
            if pub >= start:
                page_all_old = False  # 本页有不早于 start 的帖子
            if pub < start or pub > end:
                continue
            topic_id = post.get('topicID', '')
            items.append(NewsItem(
                title        = post.get('subject', ''),
                content      = post.get('subinfo', ''),
                source       = '淘股吧',
                url          = f'{TAOGUBA_ARTICLE_URL}{topic_id}',
                published_at = pub.isoformat(),
                heat         = post.get('totalViewNum', 0) or post.get('totalReplyNum', 0),
            ))

        if page_all_old:
            consecutive_all_old += 1
            if consecutive_all_old >= 2:
                break  # 连续 2 页全部早于 start，窗口已扫完
        else:
            consecutive_all_old = 0

    return SourceResult('淘股吧', True, True, items, item_count=len(items))


# ── 同花顺早报 ────────────────────────────────────────────────────────────────
# 数据通过 JS 文件返回，格式为 var thsRss = {...}，不是 HTML 页面
# 编码为 GBK，需显式设置 resp.encoding

THS_NEWS_JS_URL = 'http://stock.10jqka.com.cn/thsgd/realtimenews.js'


def scrape_ths_news(start: datetime, end: datetime) -> SourceResult:
    """抓取同花顺早报，解析 JS 文件中的 item 数组"""
    budget_start = _time.time()

    resp = fetch_with_retry(THS_NEWS_JS_URL,
                            headers={**HEADERS, 'Referer': 'https://news.10jqka.com.cn/'})
    if resp is None:
        return SourceResult('同花顺早报', True, False, [],
                            error_type='fetch_failed')

    # 请求返回后检查预算（无法中断正在阻塞的请求）
    if _time.time() - budget_start > SOURCE_BUDGET:
        return SourceResult('同花顺早报', True, False, [],
                            error_type='budget_exceeded')

    resp.encoding = 'gbk'
    text = resp.text.strip()

    # JS 外层键可能无引号（非标准 JSON），直接定位 item 数组起始位置
    idx = text.find('"item":')
    if idx == -1:
        idx = text.find('item:')
    if idx == -1:
        return SourceResult('同花顺早报', True, False, [],
                            error_type='parse_failed')

    try:
        arr_start = text.index('[', idx)
        depth, arr_end = 0, arr_start
        for i, ch in enumerate(text[arr_start:], arr_start):
            if ch == '[':
                depth += 1
            elif ch == ']':
                depth -= 1
                if depth == 0:
                    arr_end = i
                    break
        entries = _json.loads(text[arr_start:arr_end + 1])
    except Exception:
        return SourceResult('同花顺早报', True, False, [],
                            error_type='parse_failed')

    from dateutil import parser as dp
    items = []
    for entry in entries:
        try:
            pub = dp.parse(entry.get('pubDate', ''))
        except Exception:
            continue
        if not (start <= pub <= end):
            continue
        items.append(NewsItem(
            title        = entry.get('title', ''),
            content      = entry.get('content', ''),
            source       = '同花顺早报',
            url          = entry.get('url', ''),
            published_at = pub.isoformat(),
            heat         = entry.get('like', 0),
        ))

    return SourceResult('同花顺早报', True, True, items, item_count=len(items))


# ── 同花顺人气榜 ──────────────────────────────────────────────────────────────
# 实际 HTML 结构：table.m-table tbody tr，各列无 class，按位置取 td

THS_HOT_URL     = 'https://q.10jqka.com.cn/thshy/'
THS_HOT_ROW_SEL = 'table.m-table tbody tr'


def scrape_ths_hotrank() -> SourceResult:
    """抓取同花顺人气榜，解析行业排名表格"""
    resp = fetch_with_retry(THS_HOT_URL)
    if resp is None:
        return SourceResult('同花顺人气榜', True, False, [],
                            error_type='fetch_failed')

    resp.encoding = 'gbk'
    soup  = BeautifulSoup(resp.text, 'lxml')
    items = []
    now   = datetime.now().isoformat()

    for row in soup.select(THS_HOT_ROW_SEL):
        tds = row.select('td')
        if len(tds) < 3:
            continue

        rank   = tds[0].get_text(strip=True)
        name   = tds[1].get_text(strip=True)
        change = tds[2].get_text(strip=True)

        if not rank.isdigit():
            continue

        items.append(NewsItem(
            title        = name,
            content      = f'人气榜排名第{rank}，涨跌幅：{change}%',
            source       = '同花顺人气榜',
            url          = THS_HOT_URL,
            published_at = now,
            heat         = int(rank),
        ))

    return SourceResult('同花顺人气榜', True, True, items, item_count=len(items))


# ── 雪球 ──────────────────────────────────────────────────────────────────────
# 接口需要有效 Cookie，从 .env 文件的 XUEQIU_COOKIE 读取
# public_timeline_by_category?category=6 返回时间倒序的广场流（非 category=-1 的热门档案），
# 每页约 30 条，游标字段为外层 post['id']（递减序号），
# 时间倒序故可在 pub < start 时提前退出翻页。

XUEQIU_URL       = 'https://xueqiu.com/v4/statuses/public_timeline_by_category.json'
XUEQIU_COUNT     = 30
XUEQIU_MAX_PAGES = 15  # 约 19 小时窗口需 10 页，留余量至 15 页


def scrape_xueqiu(start: datetime, end: datetime) -> SourceResult:
    """抓取雪球广场流（category=6，时间倒序），用 max_id 游标分页。
    实际内容在嵌套的 data 字段（JSON 字符串）中；游标为外层 post['id']，非内层 data.id。
    """
    cookie = os.environ.get('XUEQIU_COOKIE', '').strip()
    if not cookie:
        print('[警告] XUEQIU_COOKIE 未设置，请在 .env 中配置后重试')
        return SourceResult('雪球', True, False, [], error_type='no_cookie')

    xueqiu_headers = {
        **HEADERS,
        'Referer': 'https://xueqiu.com/',
        'Cookie':  cookie,
    }

    items        = []
    max_id       = '-1'
    budget_start = _time.time()

    for page in range(1, XUEQIU_MAX_PAGES + 1):
        if _time.time() - budget_start > SOURCE_BUDGET:
            break

        params = {
            'since_id': '-1',
            'max_id':   max_id,
            'count':    str(XUEQIU_COUNT),
            'category': '6',
        }

        # 直接请求以便获取 HTTP 状态码，区分 Cookie 失效与网络错误
        try:
            resp = _requests.get(XUEQIU_URL, headers=xueqiu_headers,
                                 params=params, timeout=REQUEST_TIMEOUT)
        except Exception:
            if page == 1:
                return SourceResult('雪球', True, False, [], error_type='fetch_failed')
            break

        if resp.status_code in (401, 403):
            print(f'[警告] 雪球 Cookie 已失效（HTTP {resp.status_code}），'
                  '请从浏览器重新复制 Cookie 并更新 .env 中的 XUEQIU_COOKIE')
            return SourceResult('雪球', True, False, [], error_type='cookie_expired')

        if not resp.ok:
            print(f'[警告] 雪球请求失败（HTTP {resp.status_code}）')
            if page == 1:
                return SourceResult('雪球', True, False, [], error_type='fetch_failed')
            break

        try:
            envelope = resp.json()
        except Exception:
            if page == 1:
                return SourceResult('雪球', True, False, [], error_type='parse_failed')
            break

        # 雪球有时以 200 返回认证错误，检测 API 层面的 Cookie 失效
        if 'error_description' in envelope:
            print(f'[警告] 雪球 Cookie 已失效：{envelope.get("error_description")}，'
                  '请更新 .env 中的 XUEQIU_COOKIE')
            return SourceResult('雪球', True, False, [], error_type='cookie_expired')

        posts = envelope.get('list', [])
        if not posts:
            break

        last_id      = max_id  # 若本页无有效外层 ID，last_id == max_id，下面会 break
        hit_boundary = False

        for post in posts:
            # 游标用外层 post['id']（列表序号），与内层 data.id（内容 ID）不同
            outer_id = str(post.get('id', ''))
            if outer_id:
                last_id = outer_id

            # 实际数据在嵌套的 data 字段（可能是 JSON 字符串，需二次解析）
            raw_data = post.get('data', {})
            if isinstance(raw_data, str):
                try:
                    raw_data = _json.loads(raw_data)
                except Exception:
                    continue

            ts_ms = raw_data.get('created_at', 0)
            if not ts_ms:
                continue
            pub = datetime.fromtimestamp(ts_ms / 1000)

            if pub > end:
                continue  # 时间倒序，窗口结束后的帖子跳过（继续往下找）
            if pub < start:
                hit_boundary = True
                break        # 时间倒序，已早于窗口起点，后续帖子更旧，停止翻页

            target = raw_data.get('target', '')
            title  = raw_data.get('title', '') or raw_data.get('description', '')[:80]

            items.append(NewsItem(
                title        = title,
                content      = raw_data.get('description', ''),
                source       = '雪球',
                url          = f'https://xueqiu.com{target}' if target else 'https://xueqiu.com',
                published_at = pub.isoformat(),
                heat         = raw_data.get('reply_count', 0) or raw_data.get('view_count', 0),
            ))

        if hit_boundary:
            break
        # last_id == max_id：本页无有效外层 ID，游标未推进，避免死循环
        if last_id == max_id:
            break
        max_id = last_id

    return SourceResult('雪球', True, True, items, item_count=len(items))


# ── WebSearch 补充源 ───────────────────────────────────────────────────────────
# WebSearch 由 Claude 在 SKILL.md Step 4 执行，无法 Python 直抓。
# 本函数负责将 Claude 传入的查询结果包装成与主源统一的 SourceResult 格式，
# 确保 WebSearch 数据能以结构一致的方式进入 raw_news.json。
#
# items_data 格式（每项为 dict）：
#   title        必填  str   查询结果标题或摘要
#   content      必填  str   正文内容
#   url          可选  str   来源链接，无则传空字符串
#   published_at 可选  str   ISO 时间字符串，无则用当前时间
#   heat         可选  int   默认 0


def make_websearch_result(items_data: list) -> SourceResult:
    """
    将外部传入的 WebSearch 结果列表包装为 SourceResult。
    is_main_source=False：补充源不计入置信度计算。
    """
    if not items_data:
        return SourceResult('WebSearch', False, True, [], item_count=0)

    now = datetime.now().isoformat()
    items = []
    for d in items_data:
        items.append(NewsItem(
            title        = d.get('title', ''),
            content      = d.get('content', ''),
            source       = 'WebSearch',
            url          = d.get('url', ''),
            published_at = d.get('published_at', now),
            heat         = d.get('heat', 0),
        ))

    return SourceResult('WebSearch', False, True, items, item_count=len(items))
