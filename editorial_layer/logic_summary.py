from __future__ import annotations

import re

from editorial_layer.stock_merger import is_valid_candidate_name


SIGNAL_LABELS = {
    'recap_only': '复盘主导',
    'catalyst_only': '新催化主导',
    'mixed_recap_catalyst': '复盘与催化并存',
    'neutral': '信号中性',
}

UNIT_TYPE_LABELS = {
    'event_cluster': '同事件驱动',
    'theme_cluster': '同题材发散',
    'single': '单条独立信号',
}
_NOISY_CLUE_MARKERS = (
    '早盘', '午盘', '尾盘', '今日', '今天', '复盘', '收评', '午评', '一文看懂', '牛市', '红包',
    '急杀', '低吸', '跟随', '联合打造', '品牌', '核心原因', '行情概括', '大盘', '没话说',
)
_TITLE_PREFIX_RE = re.compile(r'^[#\[【(（\s]+')


def attach_logic_summary(sector: dict) -> dict:
    core_units = sector.get('core_logic_units', []) or []
    if not core_units:
        return {
            **sector,
            'logic_summary_short': '',
            'logic_summary_lines': [],
            'logic_summary': '',
        }

    first = core_units[0]
    unit_type = UNIT_TYPE_LABELS.get(first.get('unit_type', 'single'), '单条独立信号')
    dominant = _dominant_signal_label(sector)
    branches = _collect_branches(sector, core_units)

    short = f'{unit_type}，{dominant}'
    if branches:
        short = f'{short}，发散分支：' + '、'.join(branches[:3])

    lines = [f'结构：{unit_type}', f'信号：{dominant}']
    if branches:
        lines.append('分支：' + '、'.join(branches[:5]))

    clues = _collect_clean_clues(sector, core_units)
    if clues:
        lines.append('核心线索：' + '；'.join(clues[:3]))

    return {
        **sector,
        'logic_summary_short': short,
        'logic_summary_lines': lines,
        'logic_summary': ' | '.join(lines),
    }


def _dominant_signal_label(sector: dict) -> str:
    dist = sector.get('dominant_signals_dist', {}) or {}
    if not dist:
        return '信号中性'
    dominant_key = max(dist.items(), key=lambda kv: kv[1])[0]
    return SIGNAL_LABELS.get(dominant_key, dominant_key)


def _collect_branches(sector: dict, core_units: list[dict]) -> list[str]:
    branch_names: list[str] = []
    stock_candidates = sector.get('stock_candidates', []) or []
    for candidate in stock_candidates:
        name = (candidate.get('name') or '').strip()
        code = (candidate.get('code') or '').strip()
        if name and is_valid_candidate_name(name, code) and name not in branch_names:
            branch_names.append(name)
    if branch_names:
        return branch_names

    for unit in core_units:
        for branch in unit.get('stock_branches', []) or []:
            name = (branch.get('stock_name') or '').strip()
            code = (branch.get('stock_code') or '').strip()
            if name and is_valid_candidate_name(name, code) and name not in branch_names:
                branch_names.append(name)
    return branch_names


def _collect_clean_clues(sector: dict, core_units: list[dict]) -> list[str]:
    clues: list[str] = []
    branch_names = _collect_branches(sector, core_units)

    for unit in core_units:
        title = _normalize_clue_text(unit.get('title', ''))
        if _is_clean_clue(title):
            clues.append(title)
            continue

        unit_branch_names = [
            (branch.get('stock_name') or '').strip()
            for branch in unit.get('stock_branches', []) or []
            if is_valid_candidate_name(
                (branch.get('stock_name') or '').strip(),
                (branch.get('stock_code') or '').strip(),
            )
        ]
        if unit_branch_names:
            deduped_branch_names = list(dict.fromkeys(unit_branch_names))
            branch_clue = '相关个股：' + '、'.join(deduped_branch_names[:3])
            if branch_clue not in clues:
                clues.append(branch_clue)
            continue

        summary = _normalize_clue_text(unit.get('summary', ''))
        if _is_clean_clue(summary):
            clues.append(summary)

    if clues:
        return clues

    if branch_names:
        return ['相关个股：' + '、'.join(branch_names[:3])]

    return []


def _normalize_clue_text(text: str) -> str:
    clean = _TITLE_PREFIX_RE.sub('', (text or '').strip())
    clean = re.sub(r'\s+', ' ', clean)
    return clean[:40].strip('；;，, ')


def _is_clean_clue(text: str) -> bool:
    if not text:
        return False
    if len(text) < 4:
        return False
    if any(marker in text for marker in _NOISY_CLUE_MARKERS):
        return False
    if len(text) > 18 and any(ch in text for ch in '，；。：!?！？'):
        return False
    if text.startswith(('【', '[', '(', '（')):
        return False
    return True
