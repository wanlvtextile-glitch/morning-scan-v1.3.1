from functools import lru_cache
from pathlib import Path

_CATALYST_MAP = {
    'earnings': '业绩催化',
    'policy': '政策催化',
    'news': '新闻驱动',
    'product': '产品驱动',
    'capital': '资金驱动',
    'price': '价格驱动',
    'overseas': '海外映射',
}

_PSEUDO_STOCK_KEYWORDS = (
    '纪要', '段子', '汇总', '复盘', '早报', '午评', '收评', '机构',
    '领域', '两公司', '自主可控', 'PCB', 'CPU', 'AIDC', 'CPO',
)
_SENTENCE_NOISE_MARKERS = (
    '的', '和', '与', '及', '跟随', '联合', '打造', '原因', '早盘', '午盘', '尾盘', '今日', '更新', '品牌',
)
_INSTITUTION_PREFIXES = ('国联民生', '申万', '中信', '华泰', '天风', '国泰海通')
_RESEARCH_SUFFIXES = ('电子', '通信', '计算机', '传媒', '汽车', '机械', '军工', '医药', '轻工', '策略', '宏观')


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


def _format_driver(catalyst_types: list) -> str:
    if not catalyst_types:
        return '逻辑分支'
    labels = [_CATALYST_MAP.get(t, '新闻驱动') for t in catalyst_types]
    return '+'.join(dict.fromkeys(labels))


def _empty_candidate(name: str, code: str = '') -> dict:
    return {
        'code': code,
        'name': name,
        'mention_count': 0,
        'heat_sum': 0,
        'sources': [],
        'sample_context': '',
        'match_type': 'logic_branch',
        'catalyst_types': [],
        'driver_display': '逻辑分支',
        'authenticity': None,
        'authenticity_evidence': None,
        'core_reason': None,
        'source_summary': None,
    }


def _branch_to_candidate(branch: dict, logic_unit: dict) -> dict:
    candidate = _empty_candidate(
        name=branch.get('stock_name', ''),
        code=branch.get('stock_code', ''),
    )
    candidate['mention_count'] = max(
        1,
        branch.get('recap_count', 0) + branch.get('catalyst_count', 0),
    )
    candidate['sample_context'] = branch.get('branch_reason', '')
    candidate['core_reason'] = branch.get('branch_reason', '') or logic_unit.get('summary', '')
    candidate['source_summary'] = logic_unit.get('summary', '')
    candidate['match_type'] = 'logic_branch'
    candidate['driver_display'] = _dominant_signal_driver(branch.get('dominant_signal', 'neutral'))
    return candidate


def _dominant_signal_driver(dominant_signal: str) -> str:
    mapping = {
        'catalyst_only': '新催化',
        'recap_only': '复盘回流',
        'mixed_recap_catalyst': '复盘+催化',
        'neutral': '逻辑分支',
    }
    return mapping.get(dominant_signal, '逻辑分支')


def _merge_candidate(target: dict, incoming: dict) -> None:
    target['mention_count'] += incoming.get('mention_count', 0)
    target['heat_sum'] += incoming.get('heat_sum', 0)

    target_sources = list(target.get('sources', []))
    for source in incoming.get('sources', []):
        if source not in target_sources:
            target_sources.append(source)
    target['sources'] = target_sources

    catalyst_types = list(target.get('catalyst_types', []))
    for cat in incoming.get('catalyst_types', []):
        if cat not in catalyst_types:
            catalyst_types.append(cat)
    target['catalyst_types'] = catalyst_types
    target['driver_display'] = _format_driver(catalyst_types) if catalyst_types else target.get('driver_display', '')

    if not target.get('sample_context') and incoming.get('sample_context'):
        target['sample_context'] = incoming.get('sample_context', '')
    if not target.get('core_reason') and incoming.get('core_reason'):
        target['core_reason'] = incoming.get('core_reason')
    if not target.get('source_summary') and incoming.get('source_summary'):
        target['source_summary'] = incoming.get('source_summary')
    if target.get('match_type') != 'logic_branch':
        target['match_type'] = incoming.get('match_type', target.get('match_type', 'logic_branch'))
    if not target.get('code') and incoming.get('code'):
        target['code'] = incoming.get('code')


def _normalize_key(name: str, code: str) -> str:
    if code:
        return f'code:{code}'
    return f'name:{(name or "").strip()}'


def _is_valid_candidate_name(name: str, code: str) -> bool:
    if code:
        return True
    clean = (name or '').strip()
    if not clean:
        return False
    if any(ch.isdigit() for ch in clean):
        return False
    if any(keyword in clean for keyword in _PSEUDO_STOCK_KEYWORDS):
        return False
    if any(clean.startswith(prefix) for prefix in _INSTITUTION_PREFIXES) and clean.endswith(_RESEARCH_SUFFIXES):
        return False
    if len(clean) > 8 and any(marker in clean for marker in _SENTENCE_NOISE_MARKERS):
        return False
    stock_names = _load_stock_names()
    return clean in stock_names


def is_valid_candidate_name(name: str, code: str = '') -> bool:
    return _is_valid_candidate_name(name, code)


def merge_stock_candidates(sector: dict) -> list:
    merged: dict[str, dict] = {}

    for logic_unit in sector.get('core_logic_units', []) or []:
        for branch in logic_unit.get('stock_branches', []) or []:
            name = (branch.get('stock_name') or '').strip()
            code = (branch.get('stock_code') or '').strip()
            if not _is_valid_candidate_name(name, code):
                continue
            candidate = _branch_to_candidate(branch, logic_unit)
            key = _normalize_key(candidate.get('name', ''), candidate.get('code', ''))
            if key not in merged:
                merged[key] = candidate
            else:
                _merge_candidate(merged[key], candidate)

    result = list(merged.values())
    result.sort(key=lambda x: (-x.get('mention_count', 0), -x.get('heat_sum', 0), x.get('name', '')))
    return result
