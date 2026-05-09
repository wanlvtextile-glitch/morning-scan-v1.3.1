# 分析层入口（板块摘要构建 + 阶段判断）
# 输入：sector_identifier 结果 dict + dedup_stats + confidence + source_stats
# 输出：analysis_result dict（未写文件）
# 被谁调用：analyzer.py（_analyze 管道）

import csv
import re
from collections import Counter
from typing import Optional
from preprocessor.rules import strip_html
from sector_identifier.rules import hotrank_name_to_sector
from analysis.scorer import compute_star_rating
from analysis.stage_rules import apply_stage_rules
from analysis.output import build_analysis_output

TOP_ITEMS_PER_SECTOR = 8
TOP_STOCKS_PER_SECTOR = 6
STOCKS_DICT_PATH = 'stocks_dict.csv'

_XUEQIU_STOCK_RE = re.compile(r'\$([^$\(\)]{1,20})\((S[HZ]\d{6}|BJ\d{6})\)\$')


def load_stock_names(path: str = STOCKS_DICT_PATH) -> list:
    names: list = []
    try:
        with open(path, encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('name', '').strip()
                if len(name) >= 3:
                    names.append(name)
    except FileNotFoundError:
        pass
    names.sort(key=len, reverse=True)
    return names


def extract_stock_mentions(items: list, stock_names: Optional[list] = None) -> list:
    stocks: dict = {}

    for item in items:
        text      = strip_html(item.get('title', '') + ' ' + item.get('content', ''))
        source    = item.get('source', '')
        heat      = item.get('heat', 0)
        cat_type  = item.get('catalyst_type')
        for m in _XUEQIU_STOCK_RE.finditer(text):
            name = m.group(1).strip()
            code = m.group(2)
            if code not in stocks:
                stocks[code] = {'code': code, 'name': name,
                                'mention_count': 0, 'heat_sum': 0,
                                'sources': set(), 'sample_context': '',
                                'catalyst_types': []}
            stocks[code]['mention_count'] += 1
            stocks[code]['heat_sum']       += heat
            stocks[code]['sources'].add(source)
            if cat_type:
                stocks[code]['catalyst_types'].append(cat_type)
            if not stocks[code]['sample_context']:
                start = max(0, m.start() - 15)
                end   = min(len(text), m.end() + 40)
                stocks[code]['sample_context'] = text[start:end]

    if stock_names:
        found_names = {v['name'] for v in stocks.values()}
        for item in items:
            text      = strip_html(item.get('title', '') + ' ' + item.get('content', ''))
            source    = item.get('source', '')
            heat      = item.get('heat', 0)
            cat_type  = item.get('catalyst_type')
            for stock_name in stock_names:
                if stock_name in found_names:
                    continue
                if stock_name not in text:
                    continue
                key = f'n:{stock_name}'
                if key not in stocks:
                    pos   = text.find(stock_name)
                    start = max(0, pos - 10)
                    end   = min(len(text), pos + len(stock_name) + 30)
                    stocks[key] = {'code': '', 'name': stock_name,
                                   'mention_count': 0, 'heat_sum': 0,
                                   'sources': set(),
                                   'sample_context': text[start:end],
                                   'match_type': 'name_match',
                                   'catalyst_types': []}
                stocks[key]['mention_count'] += 1
                stocks[key]['heat_sum']       += heat
                stocks[key]['sources'].add(source)
                if cat_type:
                    stocks[key]['catalyst_types'].append(cat_type)

    result = [
        {**v, 'sources': sorted(v['sources']),
         'catalyst_types': sorted(set(v['catalyst_types']))}
        for v in stocks.values()
    ]
    result.sort(key=lambda x: (-x['mention_count'], -x['heat_sum']))
    return result[:TOP_STOCKS_PER_SECTOR]


def build_sector_summaries(sector_result: dict, stock_names: list) -> list:
    """
    接收 sector_result，构建板块摘要列表（不含阶段判断）。
    """
    sector_weighted    = sector_result['sector_weighted']
    sector_matched_kws = sector_result['sector_matched_kws']
    sector_to_hotrank  = sector_result['sector_to_hotrank']
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

        top_items = [
            {
                'title':        strip_html(x.get('title', '')),
                'content':      x.get('content_preview', ''),
                'source':       x.get('source', ''),
                'heat':         x.get('heat', 0),
                'url':          x.get('url', ''),
                'published_at': x.get('published_at', ''),
                'cross_sector_weight': round(x['_weight'], 2),
            }
            for x in items_sorted[:TOP_ITEMS_PER_SECTOR]
        ]

        primary_items = [x for x in items_sorted[:TOP_ITEMS_PER_SECTOR] if x.get('_weight', 0) >= 0.5]
        stock_mentions = extract_stock_mentions(primary_items or items_sorted[:TOP_ITEMS_PER_SECTOR], stock_names)

        cat_types  = [x['catalyst_type'] for x in w_items if x.get('catalyst_type')]
        recap_frac = round(sum(1 for x in w_items if x.get('is_recap', False)) / len(w_items), 2)

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
            'top_items':          top_items,
            'stock_mentions':     stock_mentions,
            'needs_websearch':    False,
            'recap_fraction':     recap_frac,
            'new_catalyst_count': len(cat_types),
            'catalyst_type_dist': dict(Counter(cat_types)),
            'matched_keywords':   sector_matched_kws.get(sector_name, []),
            'multi_source_agreement': len(sources) >= 3,
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
        if our_sector is None or our_sector in sector_names_built:
            continue
        existing = next((s for s in summaries if s['name'] == our_sector), None)
        if existing and existing['effective_count'] >= 2:
            continue
        if existing:
            existing['hotrank']         = {'rank': entry['rank'], 'name': entry['name'],
                                           'change_pct': entry['change_pct']}
            existing['needs_websearch'] = True
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
            'top_items':          [],
            'stock_mentions':     [],
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
) -> dict:
    """
    完整分析管道：接收 sector_result，经板块摘要构建 → hotrank补建 → 阶段判断 → 排序，
    返回 analysis_result dict（供 analyzer.py 写文件和日志打印）。
    """
    stock_names = load_stock_names()

    summaries = build_sector_summaries(sector_result, stock_names)
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
    )
