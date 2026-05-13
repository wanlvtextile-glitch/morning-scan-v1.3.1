import json
import os
import re
import time as _time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html import unescape
from typing import Iterable, Optional

import requests as _requests
from bs4 import BeautifulSoup
from dateutil import parser as dt_parser

from collector.http_client import HEADERS, REQUEST_TIMEOUT, SOURCE_BUDGET
from collector.models import NewsItem, SourceResult

APIFY_BASE_URL = 'https://api.apify.com/v2'
APIFY_POLL_INTERVAL = 3
APIFY_MAX_WAIT = 180
TELEGRAM_BASE_URL = 'https://t.me/s/'

DEFAULT_SOCIAL_CONFIG_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'config', 'social_sources.json')
)


@dataclass
class TwitterConfig:
    enabled: bool
    query_mode_first: bool
    apify_token_env: str
    actor_id: str
    max_items_per_run: int
    search_queries: list
    users: list


@dataclass
class TelegramConfig:
    enabled: bool
    max_messages_per_channel: int
    channels: list


@dataclass
class MarketFilterConfig:
    keywords: list
    stock_code_patterns: list


def _load_social_config(config_path: str = DEFAULT_SOCIAL_CONFIG_PATH) -> dict:
    with open(config_path, encoding='utf-8') as f:
        return json.load(f)


def _load_market_filter_config() -> MarketFilterConfig:
    data = _load_social_config().get('market_filters', {})
    return MarketFilterConfig(
        keywords=data.get('keywords', []),
        stock_code_patterns=data.get('stock_code_patterns', []),
    )


def _load_twitter_config() -> TwitterConfig:
    data = _load_social_config().get('twitter', {})
    return TwitterConfig(
        enabled=data.get('enabled', False),
        query_mode_first=data.get('query_mode_first', True),
        apify_token_env=data.get('apify_token_env', 'APIFY_TOKEN'),
        actor_id=data.get('actor_id', 'altimis/scweet'),
        max_items_per_run=data.get('max_items_per_run', 80),
        search_queries=data.get('search_queries', []),
        users=data.get('users', []),
    )


def _load_telegram_config() -> TelegramConfig:
    data = _load_social_config().get('telegram', {})
    return TelegramConfig(
        enabled=data.get('enabled', False),
        max_messages_per_channel=data.get('max_messages_per_channel', 20),
        channels=data.get('channels', []),
    )


def _normalize_text(text: str) -> str:
    return re.sub(r'\s+', ' ', unescape(text or '')).strip()


def _compile_market_patterns(patterns: Iterable[str]) -> list:
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns if pattern]


def _is_market_related(text: str,
                       market_filter: MarketFilterConfig,
                       compiled_patterns: Optional[list] = None) -> bool:
    normalized = _normalize_text(text).lower()
    if not normalized:
        return False

    for keyword in market_filter.keywords:
        if keyword.lower() in normalized:
            return True

    compiled = compiled_patterns or _compile_market_patterns(market_filter.stock_code_patterns)
    return any(pattern.search(text or '') for pattern in compiled)


CHINA_TZ = timezone(timedelta(hours=8))


def _parse_datetime(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = dt_parser.parse(value)
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=CHINA_TZ)
    return parsed


def _in_window(dt: Optional[datetime], start: datetime, end: datetime) -> bool:
    if dt is None:
        return False
    if dt.tzinfo is not None:
        start = start.replace(tzinfo=CHINA_TZ) if start.tzinfo is None else start.astimezone(CHINA_TZ)
        end = end.replace(tzinfo=CHINA_TZ) if end.tzinfo is None else end.astimezone(CHINA_TZ)
        dt = dt.astimezone(CHINA_TZ)
    return start <= dt <= end


def _extract_external_links(soup: BeautifulSoup) -> list:
    links = []
    for node in soup.select('a[href]'):
        href = node.get('href', '').strip()
        if not href:
            continue
        if href.startswith('/'):
            href = f'https://t.me{href}'
        links.append(href)
    return links


def _twitter_headers() -> dict:
    return {
        **HEADERS,
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
    }


def _apify_start_run(token: str, actor_id: str, payload: dict) -> tuple[Optional[str], Optional[str]]:
    url = f'{APIFY_BASE_URL}/acts/{actor_id}/runs?token={token}'
    try:
        resp = _requests.post(url, json=payload, headers=_twitter_headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json().get('data', {})
        return data.get('id'), data.get('defaultDatasetId')
    except Exception:
        return None, None


def _apify_wait_for_run(token: str, run_id: str) -> bool:
    url = f'{APIFY_BASE_URL}/actor-runs/{run_id}?token={token}'
    elapsed = 0
    while elapsed < APIFY_MAX_WAIT:
        try:
            resp = _requests.get(url, headers=_twitter_headers(), timeout=10)
            resp.raise_for_status()
            status = resp.json().get('data', {}).get('status')
            if status == 'SUCCEEDED':
                return True
            if status in ('FAILED', 'ABORTED', 'TIMED-OUT'):
                return False
        except Exception:
            pass
        _time.sleep(APIFY_POLL_INTERVAL)
        elapsed += APIFY_POLL_INTERVAL
    return False


def _apify_fetch_dataset(token: str, dataset_id: str) -> list:
    url = f'{APIFY_BASE_URL}/datasets/{dataset_id}/items?token={token}'
    try:
        resp = _requests.get(url, headers=_twitter_headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _build_twitter_query_payload(query: str, max_items: int) -> dict:
    return {
        'source_mode': 'search',
        'search_query': query,
        'search_sort': 'Latest',
        'max_items': max(20, max_items),
    }


def _build_twitter_user_payload(users: list, max_items: int) -> dict:
    return {
        'source_mode': 'profiles',
        'profile_urls': users,
        'search_sort': 'Latest',
        'max_items': max(20, max_items),
    }


def _parse_twitter_item(raw: dict,
                        start: datetime,
                        end: datetime,
                        market_filter: MarketFilterConfig,
                        compiled_patterns: list) -> Optional[NewsItem]:
    created_at = _parse_datetime(raw.get('created_at', ''))
    if not _in_window(created_at, start, end):
        return None

    user = raw.get('user') or {}
    handle = (
        user.get('screen_name')
        or user.get('username')
        or user.get('handle')
        or raw.get('handle')
        or raw.get('username')
        or 'unknown'
    )
    text = _normalize_text(raw.get('full_text') or raw.get('text') or '')
    if not text:
        return None
    if not _is_market_related(text, market_filter, compiled_patterns):
        return None

    title = f'@{handle}: {text[:70]}'
    tweet_id = str(raw.get('id_str') or raw.get('id') or '')
    url = raw.get('url') or f'https://twitter.com/{handle}/status/{tweet_id}'
    heat = int(raw.get('favorite_count') or 0) + int(raw.get('retweet_count') or 0)

    return NewsItem(
        title=title,
        content=text,
        source='Twitter',
        url=url,
        published_at=created_at.isoformat(),
        heat=heat,
    )


def scrape_twitter(start: datetime, end: datetime) -> SourceResult:
    config = _load_twitter_config()
    if not config.enabled:
        return SourceResult('Twitter', False, True, [], item_count=0)

    token = os.environ.get(config.apify_token_env, '').strip()
    if not token:
        return SourceResult('Twitter', False, False, [], error_type='no_apify_token')

    market_filter = _load_market_filter_config()
    compiled_patterns = _compile_market_patterns(market_filter.stock_code_patterns)
    all_items = []
    budget_start = _time.time()

    def _collect_rows(payload: dict) -> list:
        run_id, dataset_id = _apify_start_run(token, config.actor_id, payload)
        if not run_id or not dataset_id:
            return []
        if not _apify_wait_for_run(token, run_id):
            return []
        return _apify_fetch_dataset(token, dataset_id)

    ordered_jobs = []
    if config.query_mode_first:
        for query in config.search_queries:
            ordered_jobs.append(('search', query))
        if config.users:
            ordered_jobs.append(('profiles', config.users))
    else:
        if config.users:
            ordered_jobs.append(('profiles', config.users))
        for query in config.search_queries:
            ordered_jobs.append(('search', query))

    seen_urls = set()
    for mode, value in ordered_jobs:
        if _time.time() - budget_start > SOURCE_BUDGET:
            break
        if mode == 'search':
            rows = _collect_rows(_build_twitter_query_payload(value, config.max_items_per_run))
        else:
            rows = _collect_rows(_build_twitter_user_payload(value, config.max_items_per_run))

        for raw in rows:
            if not isinstance(raw, dict) or raw.get('noResults'):
                continue
            item = _parse_twitter_item(raw, start, end, market_filter, compiled_patterns)
            if item is None or item.url in seen_urls:
                continue
            seen_urls.add(item.url)
            all_items.append(item)

    if not ordered_jobs:
        return SourceResult('Twitter', False, True, [], item_count=0)
    if not all_items:
        return SourceResult('Twitter', False, True, [], item_count=0)
    return SourceResult('Twitter', False, True, all_items, item_count=len(all_items))


def _parse_telegram_message(node: BeautifulSoup,
                            channel: str,
                            start: datetime,
                            end: datetime,
                            market_filter: MarketFilterConfig,
                            compiled_patterns: list) -> Optional[NewsItem]:
    time_node = node.select_one('time')
    body_node = node.select_one('.tgme_widget_message_text')
    if time_node is None or body_node is None:
        return None

    published_at = _parse_datetime(time_node.get('datetime', ''))
    if not _in_window(published_at, start, end):
        return None

    content = _normalize_text(body_node.get_text(' ', strip=True))
    if not content:
        return None
    if not _is_market_related(content, market_filter, compiled_patterns):
        return None

    channel_name_node = node.select_one('.tgme_widget_message_author')
    channel_name = _normalize_text(channel_name_node.get_text(' ', strip=True)) or channel
    external_links = _extract_external_links(body_node)
    permalink_node = node.select_one('.tgme_widget_message_date')
    permalink = ''
    if permalink_node and permalink_node.has_attr('href'):
        permalink = permalink_node['href']

    title = f'{channel_name}: {content[:70]}'
    body = content
    if external_links:
        body += '\n外链: ' + ', '.join(external_links[:5])

    return NewsItem(
        title=title,
        content=body,
        source='Telegram',
        url=permalink or f'{TELEGRAM_BASE_URL}{channel}',
        published_at=published_at.isoformat(),
        heat=len(external_links),
    )


def scrape_telegram(start: datetime, end: datetime) -> SourceResult:
    config = _load_telegram_config()
    if not config.enabled:
        return SourceResult('Telegram', False, True, [], item_count=0)

    market_filter = _load_market_filter_config()
    compiled_patterns = _compile_market_patterns(market_filter.stock_code_patterns)
    items = []
    budget_start = _time.time()

    for channel in config.channels:
        if _time.time() - budget_start > SOURCE_BUDGET:
            break

        url = f'{TELEGRAM_BASE_URL}{channel}'
        try:
            resp = _requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
        except Exception:
            if not items:
                continue
            break

        soup = BeautifulSoup(resp.text, 'lxml')
        message_nodes = soup.select('.tgme_widget_message')[:config.max_messages_per_channel]
        for node in message_nodes:
            item = _parse_telegram_message(
                node,
                channel,
                start,
                end,
                market_filter,
                compiled_patterns,
            )
            if item is not None:
                items.append(item)

    return SourceResult('Telegram', False, True, items, item_count=len(items))
