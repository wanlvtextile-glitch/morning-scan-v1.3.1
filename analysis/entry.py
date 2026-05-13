# 分析层入口（板块摘要构建 + 阶段判断）
# 输入：sector_identifier 结果 dict + dedup_stats + confidence + source_stats
# 输出：analysis_result dict（未写文件）
# 被谁调用：analyzer.py（_analyze 管道）

from collections import Counter
from sector_identifier.rules import hotrank_name_to_sector
from analysis.scorer import compute_star_rating
from analysis.stage_rules import apply_stage_rules
from analysis.output import build_analysis_output

def _build_logic_unit_lookup(logic_units: list) -> dict:
    return {unit.get('unit_key', ''): unit for unit in logic_units if unit.get('unit_key')}


def _project_core_logic_unit(unit: dict) -> dict:
    stock_branches = [
        {
            'stock_name': branch.get('stock_name', ''),
            'stock_code': branch.get('stock_code', ''),
            'branch_reason': branch.get('branch_reason', ''),
            'recap_count': branch.get('recap_count', 0),
            'catalyst_count': branch.get('catalyst_count', 0),
            'dominant_signal': branch.get('dominant_signal', 'neutral'),
        }
        for branch in unit.get('stock_branches', [])[:6]
    ]
    return {
        'unit_key': unit.get('unit_key', ''),
        'unit_type': unit.get('unit_type', 'single'),
        'title': unit.get('title', ''),
        'summary': unit.get('summary', ''),
        'dominant_signal': unit.get('dominant_signal', 'neutral'),
        'signal_confidence': unit.get('signal_confidence', 'low'),
        'related_symbols_or_sectors': unit.get('related_symbols_or_sectors', []),
        'stock_branches': stock_branches,
        'recap_count': unit.get('recap_count', 0),
        'catalyst_count': unit.get('catalyst_count', 0),
        'catalyst_type_dist': unit.get('catalyst_type_dist', {}),
        'decision_reason': unit.get('decision_reason', ''),
    }


def _unit_matches_sector(unit: dict, sector_name: str) -> bool:
    related = unit.get('related_symbols_or_sectors', []) or []
    title = unit.get('title', '')
    unit_type = unit.get('unit_type', 'single')
    if unit_type == 'theme_cluster':
        return title == sector_name or sector_name in related
    return sector_name in related or title == sector_name


def _summarize_logic_units(w_items: list, logic_unit_lookup: dict, sector_name: str) -> dict:
    unit_keys = []
    for item in w_items:
        unit_key = item.get('unit_key', '')
        if unit_key and unit_key not in unit_keys:
            unit_keys.append(unit_key)

    linked_units = [
        logic_unit_lookup[key]
        for key in unit_keys
        if key in logic_unit_lookup and _unit_matches_sector(logic_unit_lookup[key], sector_name)
    ]
    linked_units.sort(
        key=lambda unit: (
            unit.get('unit_type') != 'theme_cluster',
            unit.get('unit_type') != 'event_cluster',
            -len(unit.get('stock_branches', []) or []),
            -unit.get('catalyst_count', 0),
            -unit.get('recap_count', 0),
        )
    )
    dominant_signals = Counter(unit.get('dominant_signal', 'neutral') for unit in linked_units)
    core_logic_units = [_project_core_logic_unit(unit) for unit in linked_units[:5]]
    return {
        'logic_unit_count': len(linked_units),
        'event_cluster_count': sum(1 for unit in linked_units if unit.get('unit_type') == 'event_cluster'),
        'theme_cluster_count': sum(1 for unit in linked_units if unit.get('unit_type') == 'theme_cluster'),
        'recap_unit_count': sum(1 for unit in linked_units if unit.get('dominant_signal') == 'recap_only'),
        'catalyst_unit_count': sum(1 for unit in linked_units if unit.get('dominant_signal') == 'catalyst_only'),
        'mixed_signal_unit_count': sum(
            1 for unit in linked_units if unit.get('dominant_signal') == 'mixed_recap_catalyst'
        ),
        'dominant_signals_dist': dict(dominant_signals),
        'core_logic_units': core_logic_units,
    }


def build_sector_summaries(sector_result: dict, logic_units: list | None = None) -> list:
    """
    接收 sector_result，构建板块摘要列表（不含阶段判断）。
    """
    sector_weighted    = sector_result['sector_weighted']
    sector_matched_kws = sector_result['sector_matched_kws']
    sector_to_hotrank  = sector_result['sector_to_hotrank']
    logic_unit_lookup  = _build_logic_unit_lookup(logic_units or [])
    summaries = []

    for sector_name, w_items in sector_weighted.items():
        items_sorted    = sorted(w_items, key=lambda x: x.get('heat', 0), reverse=True)
        sources         = list(set(x['source'] for x in w_items))
        effective_count = sum(x['_weight'] for x in w_items)
        heat_score      = sum(x.get('heat', 0) * x['_weight'] for x in w_items)
        unique_count    = sum(1 for x in w_items if x['_exclusive'])
        hotrank_info    = sector_to_hotrank.get(sector_name)
        hotrank_pos     = hotrank_info['rank'] if hotrank_info else None
        star_rating     = compute_star_rating(effective_count, len(sources), hotrank_pos)

        cat_types  = [x['catalyst_type'] for x in w_items if x.get('catalyst_type')]
        recap_frac = round(sum(1 for x in w_items if x.get('is_recap', False)) / len(w_items), 2)
        logic_unit_summary = _summarize_logic_units(w_items, logic_unit_lookup, sector_name)

        summaries.append({
            'name':               sector_name,
            'star_rating':        star_rating,
            'item_count':         len(w_items),
            'unique_item_count':  unique_count,
            'effective_count':    round(effective_count, 1),
            'source_count':       len(sources),
            'sources':            sorted(sources),
            'heat_score':         round(heat_score),
            'hotrank':            hotrank_info,
            'needs_websearch':    False,
            'recap_fraction':     recap_frac,
            'new_catalyst_count': len(cat_types),
            'catalyst_type_dist': dict(Counter(cat_types)),
            'matched_keywords':   sector_matched_kws.get(sector_name, []),
            'multi_source_agreement': len(sources) >= 3,
            **logic_unit_summary,
        })

    return summaries


def build_hotrank_only(sector_result: dict, existing_summaries: list) -> list:
    """
    人气榜 Top10 中出现、但 effective_count < 2 的板块补建为 star=1 合成条目。
    返回追加后的完整 summaries 列表（原列表不被修改）。
    """
    hotrank_list      = sector_result['hotrank_list']
    sector_to_hotrank = sector_result['sector_to_hotrank']
    summaries         = list(existing_summaries)
    sector_names_built = {s['name'] for s in summaries}

    for entry in hotrank_list[:10]:
        our_sector = hotrank_name_to_sector(entry['name'])
        if our_sector is None:
            continue
        existing = next((s for s in summaries if s['name'] == our_sector), None)
        if existing and existing['effective_count'] >= 2:
            continue
        if existing:
            existing['hotrank']         = {'rank': entry['rank'], 'name': entry['name'],
                                           'change_pct': entry['change_pct']}
            existing['needs_websearch'] = True
            continue
        if our_sector in sector_names_built:
            continue
        summaries.append({
            'name':               our_sector,
            'star_rating':        2 if entry['rank'] <= 3 else 1,
            'item_count':         0,
            'unique_item_count':  0,
            'effective_count':    0.0,
            'source_count':       0,
            'sources':            [],
            'heat_score':         0,
            'hotrank':            {'rank': entry['rank'], 'name': entry['name'],
                                   'change_pct': entry['change_pct']},
            'needs_websearch':    True,
            'recap_fraction':     0.0,
            'new_catalyst_count': 0,
            'catalyst_type_dist': {},
            'matched_keywords':   [],
            'multi_source_agreement': False,
        })
        sector_names_built.add(our_sector)

    return summaries


def build_hotrank_signals(hotrank_list: list, sector_summaries: list) -> list:
    sector_eff = {s['name']: s['effective_count'] for s in sector_summaries}
    signals = []
    for entry in hotrank_list[:10]:
        our_sector = hotrank_name_to_sector(entry['name'])
        eff        = sector_eff.get(our_sector, 0.0) if our_sector else 0.0
        if eff >= 5:
            sig_type = 'news_driven'
        elif eff >= 2:
            sig_type = 'hotrank_weak'
        else:
            sig_type = 'hotrank_only'
        signals.append({
            'rank':            entry['rank'],
            'hotrank_name':    entry['name'],
            'change_pct':      entry['change_pct'],
            'mapped_sector':   our_sector,
            'effective_count': round(eff, 1),
            'signal_type':     sig_type,
        })
    return signals


def run_analysis_pipeline(
    sector_result: dict,
    dedup_stats: dict,
    confidence: str,
    source_stats: list,
    preprocess_context: dict | None = None,
) -> dict:
    """
    完整分析管道：接收 sector_result，经板块摘要构建 → hotrank补建 → 阶段判断 → 排序，
    返回 analysis_result dict（供 analyzer.py 写文件和日志打印）。
    """
    if preprocess_context is None:
        preprocess_context = {}

    logic_units = preprocess_context.get('logic_units', [])
    signal_stats = preprocess_context.get('signal_stats', {})
    dedup_decisions = preprocess_context.get('dedup_decisions', [])

    summaries = build_sector_summaries(sector_result, logic_units=logic_units)
    summaries = build_hotrank_only(sector_result, summaries)

    # 阶段判断
    for s in summaries:
        stage, signals = apply_stage_rules(s)
        s['stage']         = stage
        s['stage_signals'] = signals

    # 排序
    summaries.sort(key=lambda s: (
        -s['star_rating'],
        s['hotrank']['rank'] if s['hotrank'] else 999,
        -s['source_count'],
        -s['effective_count'],
    ))

    hotrank_signals = build_hotrank_signals(sector_result['hotrank_list'], summaries)

    return build_analysis_output(
        confidence, source_stats, dedup_stats,
        summaries, sector_result['hotrank_list'], hotrank_signals,
        len(sector_result['unmatched']),
        preprocess_signal_stats=signal_stats,
        dedup_decisions=dedup_decisions,
    )
