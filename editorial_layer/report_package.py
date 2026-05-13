# 编辑层：report_package 构建
# 从 editorial_result 组装最终的结构化数据包（report_package），
# 供 output_layer 渲染 markdown / brief_markdown 使用，
# 也可直接被外部消费（JSON 化存档、下游 API 等）。
#
# report_package 结构：
#   meta             - 元信息（日期、置信度、版本）
#   source_snapshot  - 规范化采集状态列表
#   market_context   - 市场背景（含 Claude 占位字段）
#   sector_intelligence - 全部板块（含 group / stock_candidates / 双评分）
#   stock_pool       - 跨板块展平的个股候选列表
#   report_views     - 报告视图（top_sectors / hidden_signals / groups / 结论）
#
# 被谁调用：output_layer/entry.py (build_report_from_editorial)

from datetime import datetime
from editorial_layer.logic_summary import attach_logic_summary
from editorial_layer.stock_merger import is_valid_candidate_name
from output_layer.rules import GROUP_ORDER, GROUP_排除项

VERSION = '1.2'


def _build_source_snapshot(source_stats: list) -> list:
    """将 source_stats 规范化为含 status 图标的快照列表"""
    snapshot = []
    for s in source_stats:
        if s.get('fetch_success') and s.get('item_count', 0) > 0:
            status = '✅'
        elif s.get('fetch_success'):
            status = '⚠️'
        else:
            status = '❌'
        snapshot.append({
            'name':         s.get('name', ''),
            'source_type':  s.get('source_type', ''),
            'is_main':      s.get('is_main', False),
            'status':       status,
            'item_count':   s.get('item_count', 0),
            'fetch_success': s.get('fetch_success', False),
            'error_type':   s.get('error_type'),
        })
    return snapshot


def _build_stock_pool(stock_pool_by_sector: dict) -> list:
    """展平 stock_pool_by_sector → 带 sector 字段的列表"""
    pool = []
    for sector_name, candidates in stock_pool_by_sector.items():
        for c in candidates:
            pool.append({**c, 'sector': sector_name})
    return pool


def _display_candidates(candidates: list) -> list:
    return [
        candidate
        for candidate in (candidates or [])
        if is_valid_candidate_name(candidate.get('name', ''), candidate.get('code', ''))
    ]


def _prepare_sector_for_display(sector: dict) -> dict:
    return attach_logic_summary({
        **sector,
        'stock_candidates': _display_candidates(sector.get('stock_candidates', [])),
    })


def _build_groups(all_sectors: list) -> dict:
    """从 all_sectors 构建按栏目分组的 dict（向后兼容 output_layer.output 格式）"""
    groups: dict = {g: [] for g in GROUP_ORDER}
    for s in all_sectors:
        g = s.get('group', GROUP_排除项)
        if g in groups:
            groups[g].append(s)
    return groups


def _build_trigger_summary(all_sectors: list) -> list:
    """汇总非排除项板块的盘中验证点"""
    result = []
    for s in all_sectors:
        if s.get('group') == GROUP_排除项:
            continue
        for tp in s.get('trigger_points', []):
            result.append({'sector': s['name'], 'point': tp})
    return result


def build_report_package(editorial_result: dict) -> dict:
    """
    从 editorial_result 构建 report_package。

    report_package 字段一览：
      meta             {generated_at, date, confidence, version}
      source_snapshot  [{name, status, item_count, ...}]
      market_context   {scan_date, dedup_stats, indices=None, us_markets=None, ...}
      sector_intelligence [sector dict + stock_candidates]
      stock_pool       [{sector, code, name, authenticity=None, ...}]
      report_views     {top_sectors, hidden_signals, final_recommendations,
                        groups, trigger_summary}
    """
    date        = editorial_result.get('date', datetime.now().strftime('%Y-%m-%d'))
    confidence  = editorial_result.get('confidence', 'unknown')
    all_sectors = [_prepare_sector_for_display(s) for s in editorial_result.get('all_sectors', [])]
    top_sectors = [_prepare_sector_for_display(s) for s in editorial_result.get('top_sectors', [])]

    return {
        'meta': {
            'generated_at': datetime.now().isoformat(),
            'date':         date,
            'confidence':   confidence,
            'version':      VERSION,
        },
        'source_snapshot':    _build_source_snapshot(editorial_result.get('source_stats', [])),
        'market_context':     editorial_result.get('market_context', {}),
        'sector_intelligence': all_sectors,
        'stock_pool':         _build_stock_pool(editorial_result.get('stock_pool_by_sector', {})),
        'report_views': {
            'top_sectors':           top_sectors,
            'hidden_signals':        editorial_result.get('hidden_signals', []),
            'final_recommendations': editorial_result.get('final_recommendations', {}),
            'groups':                _build_groups(all_sectors),
            'trigger_summary':       _build_trigger_summary(all_sectors),
        },
    }
