from __future__ import annotations

import re
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

from preprocessor.rules import strip_html


THEME_KEYWORDS: dict[str, list[str]] = {
    '液冷': ['液冷', '冷板', '散热', 'Coolermaster', '机架级热管'],
    'AI算力': ['算力', '服务器', 'GPU', 'CPU', '光模块', 'CPO', '数据中心'],
    '半导体': ['半导体', '芯片', '晶圆', '存储', '封测', '先进封装'],
    '能源金属': ['稀土', '白银', '铜', '镍', '钴', '锂', '碳酸锂', '能源金属'],
    '军工': ['军工', '导弹', '战机', '卫星', '航天', '雷达'],
    '机器人': ['机器人', '人形机器人', '机械臂', '减速器', '丝杠'],
    '创新药': ['创新药', '药物', '药企', '临床', '适应症', '医保'],
    '新能源': ['新能源', '光伏', '风电', '储能', '锂电', '电池'],
}

EVENT_ACTION_KEYWORDS = ['发布', '出台', '宣布', '应对', '实施', '启动', '签署', '通过']
EVENT_CAUSE_KEYWORDS = [
    '能源危机', '紧急法令', '供给担忧', '停产', '减产', '事故', '网攻', '堵路',
    '制裁', '关税', '地缘冲突', '收购', '并购', '复产推迟',
]
_ENTITY_ACTION_RE = re.compile(
    r'([\u4e00-\u9fffA-Za-z]{2,16})(?:正式)?(?:发布|出台|宣布|应对|实施|启动|签署|通过)'
)
_BRACKET_RE = re.compile(r'【([^【】]{2,20})】')
_TITLE_STOCK_RE = re.compile(r'([\u4e00-\u9fffA-Za-z]{2,12})[!！:：丨|（(]')
_RAW_CANDIDATE_RE = re.compile(r'[A-Za-z\u4e00-\u9fff]{2,12}')
_COMPANY_NAME_RE = re.compile(
    r'([\u4e00-\u9fffA-Za-z]{2,12}(?:股份|科技|电气|电子|精密|材料|通信|能源|智家|集团|电力|光电|新材))'
)
_PSEUDO_STOCK_PREFIXES = ('更新', '复盘', '今日', '机构', '国联', '申万', '中信', '华泰', '天风')
_PSEUDO_STOCK_KEYWORDS = (
    '纪要', '段子', '汇总', '标题', '复盘', '收评', '午评', '早报', '机构', '研究',
    '策略', '领域', '两公司', '自主可控', 'PCB', 'CPU', 'AIDC', 'CPO',
)
_SENTENCE_NOISE_MARKERS = (
    '的', '和', '与', '及', '跟随', '联合', '打造', '原因', '早盘', '午盘', '尾盘', '今日', '更新', '品牌',
)
_SENTENCE_CONTEXT_MARKERS = ('联合打造', '跟随', '原因', '品牌', '早盘', '午盘', '尾盘', '今日')


@lru_cache(maxsize=1)
def _load_stock_names() -> set[str]:
    csv_path = Path(__file__).resolve().parents[1] / 'data' / 'stocks_dict.csv'
    names: set[str] = set()
    for encoding in ('utf-8', 'gbk', 'gb18030'):
        try:
            with csv_path.open(encoding=encoding) as f:
                next(f, None)
                for line in f:
                    name = line.strip()
                    if name:
                        names.add(name)
            if names:
                return names
        except FileNotFoundError:
            return set()
        except UnicodeDecodeError:
            names.clear()
            continue
    return names


def _build_text(item: dict) -> str:
    return strip_html((item.get('title', '') or '') + ' ' + (item.get('content', '') or ''))


def detect_themes(item: dict) -> list[str]:
    text = _build_text(item)
    matched = []
    for theme, keywords in THEME_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            matched.append(theme)
    return matched


def build_event_key(item: dict) -> str:
    text = _build_text(item)
    entity_match = _ENTITY_ACTION_RE.search(text)
    entity = entity_match.group(1) if entity_match else ''
    action = next((kw for kw in EVENT_ACTION_KEYWORDS if kw in text), '')
    cause = next((kw for kw in EVENT_CAUSE_KEYWORDS if kw in text), '')
    if entity and action and cause:
        return f'{entity}|{action}|{cause}'
    return ''


def _looks_like_pseudo_stock(name: str, themes: list[str]) -> bool:
    if not name:
        return True
    if name in themes:
        return True
    if any(ch.isdigit() for ch in name):
        return True
    if any(keyword in name for keyword in _PSEUDO_STOCK_KEYWORDS):
        return True
    if any(name.startswith(prefix) for prefix in _PSEUDO_STOCK_PREFIXES):
        return True
    if len(name) > 8 and any(marker in name for marker in _SENTENCE_NOISE_MARKERS):
        return True
    return False


def _is_noisy_match_context(text: str, start: int, end: int) -> bool:
    left = text[max(0, start - 6):start]
    right = text[end:min(len(text), end + 8)]
    around = left + text[start:end] + right
    if any(marker in around for marker in _SENTENCE_CONTEXT_MARKERS):
        return True
    if left.endswith(('由', '从', '被', '让', '将', '把', '出')):
        return True
    if right.startswith(('与', '和', '及', '的')):
        return True
    return False


def _extract_known_stock_name(text: str, themes: list[str]) -> str:
    stock_names = _load_stock_names()
    if not text or not stock_names:
        stock_names = set()

    matches: list[str] = []
    for match in _RAW_CANDIDATE_RE.finditer(text):
        name = match.group(0).strip()
        if name in stock_names and not _looks_like_pseudo_stock(name, themes):
            if _is_noisy_match_context(text, match.start(), match.end()):
                continue
            matches.append(name)

    if not matches:
        for match in _COMPANY_NAME_RE.finditer(text):
            name = match.group(1).strip()
            if not _looks_like_pseudo_stock(name, themes):
                if _is_noisy_match_context(text, match.start(1), match.end(1)):
                    continue
                matches.append(name)

    if not matches:
        return ''

    matches.sort(key=len, reverse=True)
    return matches[0]


def _extract_branch_name(item: dict, themes: list[str]) -> str:
    title = item.get('title', '') or ''
    content = item.get('content', '') or ''
    stock_names = _load_stock_names()

    direct_title_match = _extract_known_stock_name(title, themes)
    if direct_title_match:
        return direct_title_match

    bracket = _BRACKET_RE.search(title)
    if bracket:
        name = bracket.group(1).strip()
        if name in stock_names and not _looks_like_pseudo_stock(name, themes):
            return name

    title_stock = _TITLE_STOCK_RE.search(title)
    if title_stock:
        name = title_stock.group(1).strip()
        if name in stock_names and not _looks_like_pseudo_stock(name, themes):
            return name

    direct_content_match = _extract_known_stock_name(content, themes)
    if direct_content_match:
        return direct_content_match

    return ''


def _summarize_item(item: dict) -> str:
    preview = (item.get('content_preview', '') or '').strip()
    if preview:
        return preview
    content = strip_html(item.get('content', '') or '')
    if content:
        return content[:80]
    return strip_html(item.get('title', '') or '')


def _signal_stats(items: list[dict]) -> tuple[int, int, dict[str, int], str]:
    recap_count = sum(1 for item in items if item.get('is_recap'))
    catalyst_types = [item.get('catalyst_type') for item in items if item.get('catalyst_type')]
    catalyst_count = len(catalyst_types)
    if recap_count > 0 and catalyst_count == 0:
        dominant = 'recap_only'
    elif recap_count == 0 and catalyst_count > 0:
        dominant = 'catalyst_only'
    elif recap_count > 0 and catalyst_count > 0:
        dominant = 'mixed_recap_catalyst'
    else:
        dominant = 'neutral'
    return recap_count, catalyst_count, dict(Counter(catalyst_types)), dominant


def _signal_confidence(items: list[dict], dominant_signal: str) -> str:
    if len(items) >= 3 and dominant_signal != 'neutral':
        return 'high'
    if len(items) >= 2 or dominant_signal != 'neutral':
        return 'medium'
    return 'low'


def _make_logic_unit(
    unit_key: str,
    unit_type: str,
    title: str,
    summary: str,
    items: list[dict],
    related_symbols_or_sectors: list[str] | None = None,
    stock_branches: list[dict] | None = None,
    decision_reason: str = '',
) -> dict:
    recap_count, catalyst_count, catalyst_type_dist, dominant_signal = _signal_stats(items)
    return {
        'unit_key': unit_key,
        'unit_type': unit_type,
        'title': title,
        'summary': summary,
        'items': items,
        'main_item': items[0] if items else None,
        'related_symbols_or_sectors': related_symbols_or_sectors or [],
        'stock_branches': stock_branches or [],
        'recap_count': recap_count,
        'catalyst_count': catalyst_count,
        'catalyst_type_dist': catalyst_type_dist,
        'dominant_signal': dominant_signal,
        'signal_confidence': _signal_confidence(items, dominant_signal),
        'decision_reason': decision_reason,
    }


def build_logic_units(processed_items: list[dict]) -> list[dict]:
    event_buckets: dict[str, list[dict]] = defaultdict(list)
    theme_buckets: dict[str, list[dict]] = defaultdict(list)
    singles: list[dict] = []

    for item in processed_items:
        themes = detect_themes(item)
        item['_themes'] = themes
        item['_event_key'] = build_event_key(item)
        item['_branch_name'] = _extract_branch_name(item, themes)
        if item['_event_key']:
            event_buckets[item['_event_key']].append(item)
        else:
            singles.append(item)

    logic_units: list[dict] = []
    assigned_ids: set[str] = set()

    for event_key, items in event_buckets.items():
        if len(items) < 2:
            singles.extend(items)
            continue
        title = strip_html(items[0].get('title', '') or event_key)
        summary = _summarize_item(items[0])
        related = sorted({theme for item in items for theme in item.get('_themes', [])})
        unit_key = f'event::{event_key}'
        for item in items:
            item['unit_key'] = unit_key
            item['preprocess_role'] = 'event_supporting_item'
            item['decision_type'] = 'merge_into_event'
            assigned_ids.add(item['original_id'])
        logic_units.append(_make_logic_unit(
            unit_key=unit_key,
            unit_type='event_cluster',
            title=title,
            summary=summary,
            items=items,
            related_symbols_or_sectors=related,
            decision_reason='same event cluster',
        ))

    remaining = [item for item in singles if item['original_id'] not in assigned_ids]
    for item in remaining:
        themes = item.get('_themes', [])
        if themes:
            theme_buckets[themes[0]].append(item)

    themed_ids: set[str] = set()
    for theme, items in theme_buckets.items():
        branch_names = {item.get('_branch_name', '') for item in items if item.get('_branch_name')}
        if not branch_names:
            continue

        unit_key = f'theme::{theme}'
        stock_branch_map: dict[str, list[dict]] = defaultdict(list)
        for item in items:
            branch_name = item.get('_branch_name', '')
            if not branch_name:
                continue
            stock_branch_map[branch_name].append(item)
            item['unit_key'] = unit_key
            item['preprocess_role'] = 'theme_branch_item'
            item['decision_type'] = 'merge_into_theme'
            themed_ids.add(item['original_id'])

        if not stock_branch_map:
            continue

        stock_branches = []
        for branch_name, branch_items in stock_branch_map.items():
            recap_count, catalyst_count, _, dominant_signal = _signal_stats(branch_items)
            stock_branches.append({
                'stock_name': branch_name,
                'stock_code': '',
                'branch_reason': _summarize_item(branch_items[0]),
                'supporting_items': branch_items,
                'recap_count': recap_count,
                'catalyst_count': catalyst_count,
                'dominant_signal': dominant_signal,
            })

        logic_units.append(_make_logic_unit(
            unit_key=unit_key,
            unit_type='theme_cluster',
            title=theme,
            summary=f'{theme}题材下出现多标的分支发散',
            items=items,
            related_symbols_or_sectors=[theme],
            stock_branches=stock_branches,
            decision_reason='same theme with validated stock branches',
        ))

    for item in processed_items:
        if item['original_id'] in assigned_ids or item['original_id'] in themed_ids:
            continue
        unit_key = f'single::{item["original_id"]}'
        item['unit_key'] = unit_key
        item['preprocess_role'] = 'standalone_item'
        item['decision_type'] = 'keep'
        stock_branches = []
        branch_name = item.get('_branch_name', '')
        if branch_name:
            recap_count, catalyst_count, _, dominant_signal = _signal_stats([item])
            stock_branches.append({
                'stock_name': branch_name,
                'stock_code': '',
                'branch_reason': _summarize_item(item),
                'supporting_items': [item],
                'recap_count': recap_count,
                'catalyst_count': catalyst_count,
                'dominant_signal': dominant_signal,
            })
        logic_units.append(_make_logic_unit(
            unit_key=unit_key,
            unit_type='single',
            title=strip_html(item.get('title', '') or ''),
            summary=_summarize_item(item),
            items=[item],
            related_symbols_or_sectors=item.get('_themes', []),
            stock_branches=stock_branches,
            decision_reason='standalone item',
        ))

    for item in processed_items:
        item.pop('_themes', None)
        item.pop('_event_key', None)
        item.pop('_branch_name', None)

    return logic_units


def build_signal_stats(logic_units: list[dict], exact_duplicate_removed: int) -> dict:
    stats = Counter(unit.get('dominant_signal', 'neutral') for unit in logic_units)
    return {
        'recap_only_units': stats.get('recap_only', 0),
        'catalyst_only_units': stats.get('catalyst_only', 0),
        'mixed_units': stats.get('mixed_recap_catalyst', 0),
        'neutral_units': stats.get('neutral', 0),
        'total_recap_items': sum(unit.get('recap_count', 0) for unit in logic_units),
        'total_catalyst_items': sum(unit.get('catalyst_count', 0) for unit in logic_units),
        'event_cluster_count': sum(1 for unit in logic_units if unit.get('unit_type') == 'event_cluster'),
        'theme_cluster_count': sum(1 for unit in logic_units if unit.get('unit_type') == 'theme_cluster'),
        'exact_duplicate_removed': exact_duplicate_removed,
    }
