import json
import os
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from glob import glob
from typing import Optional
from urllib.parse import quote

import requests as _requests

from collector.http_client import HEADERS, REQUEST_TIMEOUT
from collector.models import NewsItem, SourceResult
from collector.social_sources import (
    _in_window,
    _normalize_text,
    _parse_datetime,
)

DEFAULT_ZSXQ_CONFIG_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'config', 'zsxq_source.json')
)
DEFAULT_ENV_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', '.env')
)

_CURL_HEADER_RE = re.compile(r"""-H\s+(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)')""")
_EMBED_TAG_RE = re.compile(r"<e\b[^>]*title=\"([^\"]+)\"[^>]*/>")


@dataclass
class ZsxqConfig:
    enabled: bool
    group_id: str
    topics_count: int
    sticky_count: int
    scope: str
    max_pages: int
    timestamp_offset_ms: int
    request_delay_seconds: float
    curl_env: str
    topics_response_file: str
    topics_response_dir: str
    sticky_response_file: str


def _load_zsxq_config(config_path: str = DEFAULT_ZSXQ_CONFIG_PATH) -> ZsxqConfig:
    with open(config_path, encoding='utf-8') as f:
        data = json.load(f)
    return ZsxqConfig(
        enabled=data.get('enabled', False),
        group_id=str(data.get('group_id', '')).strip(),
        topics_count=int(data.get('topics_count', 20)),
        sticky_count=int(data.get('sticky_count', 3)),
        scope=data.get('scope', 'all'),
        max_pages=int(data.get('max_pages', 20)),
        timestamp_offset_ms=int(data.get('timestamp_offset_ms', 1)),
        request_delay_seconds=float(data.get('request_delay_seconds', 0.5)),
        curl_env=data.get('curl_env', 'ZSXQ_TOPICS_CURL'),
        topics_response_file=data.get('topics_response_file', 'data/zsxq_topics_response.json'),
        topics_response_dir=data.get('topics_response_dir', 'data/zsxq_topics_pages'),
        sticky_response_file=data.get('sticky_response_file', 'data/zsxq_sticky_response.json'),
    )


def _extract_headers_from_curl(curl_text: str) -> dict:
    headers = {}
    for double_quoted, single_quoted in _CURL_HEADER_RE.findall(curl_text or ''):
        raw = double_quoted or single_quoted
        raw = raw.replace('\\"', '"').replace("\\'", "'")
        if ':' not in raw:
            continue
        key, value = raw.split(':', 1)
        headers[key.strip()] = value.strip()
    return headers


def _load_local_env(path: str = DEFAULT_ENV_PATH) -> dict:
    values = {}
    if not os.path.exists(path):
        return values

    with open(path, encoding='utf-8') as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            if key and key not in values:
                values[key] = value
    return values


def _build_zsxq_headers(config: ZsxqConfig) -> dict:
    headers = dict(HEADERS)
    local_env = _load_local_env()

    curl_text = os.environ.get(config.curl_env, local_env.get(config.curl_env, '')).strip()
    if curl_text:
        headers.update(_extract_headers_from_curl(curl_text))

    env_header_map = {
        'ZSXQ_COOKIE': 'Cookie',
        'ZSXQ_AUTHORIZATION': 'Authorization',
        'ZSXQ_X_VERSION': 'X-Version',
        'ZSXQ_X_SIGNATURE': 'X-Signature',
        'ZSXQ_X_TIMESTAMP': 'X-Timestamp',
        'ZSXQ_X_ADUID': 'X-Aduid',
        'ZSXQ_X_REQUEST_ID': 'X-Request-Id',
        'ZSXQ_REFERER': 'Referer',
        'ZSXQ_USER_AGENT': 'User-Agent',
    }
    for env_name, header_name in env_header_map.items():
        value = os.environ.get(env_name, local_env.get(env_name, '')).strip()
        if value:
            headers[header_name] = value

    return headers


def _prepare_request_headers(headers: dict) -> dict:
    request_headers = dict(headers)
    request_headers['X-Timestamp'] = str(int(time.time()))
    request_headers['X-Request-Id'] = str(uuid.uuid4())
    return request_headers


def _replace_embed_tags(text: str) -> str:
    return _EMBED_TAG_RE.sub(lambda match: match.group(1), text or '')


def _topic_owner_name(topic: dict) -> str:
    talk = topic.get('talk') or {}
    owner = talk.get('owner') or {}
    return _normalize_text(owner.get('name', ''))


def _topic_text(topic: dict) -> str:
    topic_type = topic.get('type')
    files = topic.get('files') or []
    file_names = [_normalize_text(file_item.get('name', '')) for file_item in files]
    file_names = [name for name in file_names if name]
    file_summary = ''
    if file_names:
        file_summary = 'Attachments: ' + '; '.join(file_names[:5])

    if topic_type == 'talk':
        text = _normalize_text(_replace_embed_tags((topic.get('talk') or {}).get('text', '')))
    elif topic_type == 'question':
        text = _normalize_text(_replace_embed_tags((topic.get('question') or {}).get('text', '')))
    elif topic_type == 'answer':
        text = _normalize_text(_replace_embed_tags((topic.get('answer') or {}).get('text', '')))
    else:
        text = ''

    if file_summary and (not text or len(text) <= 24):
        if text:
            return f'{text}\n\n{file_summary}'
        return file_summary
    return text


def _topic_title(topic: dict, text: str) -> str:
    title = _normalize_text(topic.get('title', ''))
    if title:
        return title
    owner_name = _topic_owner_name(topic)
    prefix = f'{owner_name}: ' if owner_name else ''
    return prefix + text[:80]


def _topic_url(config: ZsxqConfig, topic: dict) -> str:
    topic_id = topic.get('topic_id') or topic.get('topic_uid') or ''
    return f'https://wx.zsxq.com/group/{config.group_id}/topic/{topic_id}'


def _topic_heat(topic: dict) -> int:
    return int(topic.get('likes_count') or 0) + int(topic.get('comments_count') or 0)


def _parse_topic(config: ZsxqConfig,
                 topic: dict,
                 start: datetime,
                 end: datetime,
                 compiled_patterns: list) -> Optional[NewsItem]:
    created_at = _parse_datetime(topic.get('create_time', ''))
    if not _in_window(created_at, start, end):
        return None

    text = _topic_text(topic)
    if not text:
        return None

    return NewsItem(
        title=_topic_title(topic, text),
        content=text,
        source='ZSXQ',
        url=_topic_url(config, topic),
        published_at=created_at.isoformat(),
        heat=_topic_heat(topic),
    )


def _extract_topics_page(payload: dict) -> tuple[list, str]:
    if not payload.get('succeeded'):
        return [], ''
    data = payload.get('resp_data', {})
    topics = data.get('topics', [])
    next_end_time = str(data.get('end_time') or '').strip()
    return topics, next_end_time


def _extract_topics_from_payload(payload: dict) -> list:
    if not payload.get('succeeded'):
        return []
    return payload.get('resp_data', {}).get('topics', [])


def _fetch_topics(url: str, headers: dict) -> list:
    resp = _requests.get(url, headers=_prepare_request_headers(headers), timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return _extract_topics_from_payload(resp.json())


def _fetch_topics_page(url: str, headers: dict) -> tuple[list, str]:
    last_exc = None
    for attempt in range(3):
        try:
            resp = _requests.get(url, headers=_prepare_request_headers(headers), timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            topics, next_end_time = _extract_topics_page(resp.json())
            if topics or attempt == 2:
                return topics, next_end_time
            time.sleep(0.4 * (attempt + 1))
        except Exception as exc:
            last_exc = exc
            if attempt == 2:
                raise
            time.sleep(0.4 * (attempt + 1))

    if last_exc is not None:
        raise last_exc
    return [], ''


def _resolve_path(relative_or_absolute: str) -> str:
    if os.path.isabs(relative_or_absolute):
        return relative_or_absolute
    return os.path.normpath(
        os.path.join(os.path.dirname(__file__), '..', relative_or_absolute)
    )


def _load_topics_from_response_file(path_value: str) -> list:
    path = _resolve_path(path_value)
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        payload = json.load(f)
    return _extract_topics_from_payload(payload)


def _load_topics_from_response_dir(path_value: str) -> list:
    path = _resolve_path(path_value)
    if not os.path.isdir(path):
        return []

    topics = []
    for file_path in sorted(glob(os.path.join(path, '*.json'))):
        with open(file_path, encoding='utf-8') as f:
            payload = json.load(f)
        topics.extend(_extract_topics_from_payload(payload))
    return topics


def _dedupe_topics(topics: list) -> list:
    deduped = []
    seen_topic_ids = set()
    for topic in topics:
        topic_id = topic.get('topic_id') or topic.get('topic_uid')
        if topic_id in seen_topic_ids:
            continue
        seen_topic_ids.add(topic_id)
        deduped.append(topic)
    return deduped


def _topic_page_bounds(topics: list) -> tuple[Optional[datetime], Optional[datetime]]:
    created_times = []
    for topic in topics:
        try:
            created_times.append(_parse_datetime(topic.get('create_time', '')))
        except Exception:
            continue
    if not created_times:
        return None, None
    return max(created_times), min(created_times)


def _format_zsxq_datetime(dt: datetime) -> str:
    millis = dt.microsecond // 1000
    return dt.strftime('%Y-%m-%dT%H:%M:%S.') + f'{millis:03d}' + dt.strftime('%z')


def _next_end_time_from_topics(topics: list, offset_ms: int) -> str:
    if not topics:
        return ''

    last_topic = topics[-1]
    last_create_time = str(last_topic.get('create_time') or '').strip()
    if not last_create_time:
        return ''

    try:
        last_dt = _parse_datetime(last_create_time)
    except Exception:
        return ''

    prev_dt = last_dt.timestamp() - (max(offset_ms, 1) / 1000.0)
    return _format_zsxq_datetime(datetime.fromtimestamp(prev_dt, tz=last_dt.tzinfo))


def _build_topics_page_url(config: ZsxqConfig, end_time_cursor: str = '') -> str:
    url = (
        f'https://api.zsxq.com/v2/groups/{config.group_id}/topics'
        f'?scope={config.scope}&count={config.topics_count}'
    )
    if end_time_cursor:
        url += f'&end_time={quote(end_time_cursor, safe="")}'
    return url


def _fetch_topics_window(config: ZsxqConfig,
                         headers: dict,
                         start: datetime,
                         end: datetime) -> list:
    topics = []
    end_time_cursor = ''

    for page_index in range(config.max_pages):
        page_url = _build_topics_page_url(config, end_time_cursor)
        page_topics, next_end_time = _fetch_topics_page(page_url, headers)
        if not page_topics:
            break

        topics.extend(page_topics)
        newest_created_at, oldest_created_at = _topic_page_bounds(page_topics)

        if oldest_created_at is not None and oldest_created_at < start:
            break
        if newest_created_at is not None and newest_created_at < start:
            break
        if not next_end_time:
            next_end_time = _next_end_time_from_topics(page_topics, config.timestamp_offset_ms)

        if not next_end_time or next_end_time == end_time_cursor:
            break

        end_time_cursor = next_end_time
        if page_index + 1 < config.max_pages and config.request_delay_seconds > 0:
            time.sleep(config.request_delay_seconds)

    return _dedupe_topics(topics)


def scrape_zsxq(start: datetime, end: datetime) -> SourceResult:
    config = _load_zsxq_config()
    if not config.enabled:
        return SourceResult('ZSXQ', False, True, [], item_count=0)

    try:
        paged_topics = _load_topics_from_response_dir(config.topics_response_dir)
        single_page_topics = _load_topics_from_response_file(config.topics_response_file)
        sticky_topics = _load_topics_from_response_file(config.sticky_response_file)
        topics = _dedupe_topics(paged_topics + single_page_topics)
    except Exception as exc:
        return SourceResult('ZSXQ', False, False, [], error_type=f'file_parse_failed:{type(exc).__name__}')

    live_headers = _build_zsxq_headers(config)
    has_live_mode = bool(live_headers.get('Authorization') or live_headers.get('Cookie'))

    if has_live_mode:
        sticky_url = (
            f'https://api.zsxq.com/v2/groups/{config.group_id}/topics/sticky'
            f'?count={config.sticky_count}'
        )
        try:
            topics = _fetch_topics_window(config, live_headers, start, end)
            sticky_topics = _fetch_topics(sticky_url, live_headers)
        except Exception as exc:
            if not topics and not sticky_topics:
                return SourceResult('ZSXQ', False, False, [], error_type=f'fetch_failed:{type(exc).__name__}')

    if not topics and not sticky_topics:
        if 'X-Version' not in live_headers:
            return SourceResult('ZSXQ', False, False, [], error_type='missing_curl_headers')

        sticky_url = (
            f'https://api.zsxq.com/v2/groups/{config.group_id}/topics/sticky'
            f'?count={config.sticky_count}'
        )

        try:
            topics = _fetch_topics_window(config, live_headers, start, end)
            sticky_topics = _fetch_topics(sticky_url, live_headers)
        except Exception as exc:
            return SourceResult('ZSXQ', False, False, [], error_type=f'fetch_failed:{type(exc).__name__}')

    items = []
    for topic in _dedupe_topics(sticky_topics + topics):
        item = _parse_topic(config, topic, start, end, [])
        if item is not None:
            items.append(item)

    return SourceResult('ZSXQ', False, True, items, item_count=len(items))
