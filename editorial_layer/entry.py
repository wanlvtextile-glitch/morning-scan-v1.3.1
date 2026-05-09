# 编辑层主入口
# 职责：在 dual_score 之后、output_layer 之前，
#   1. 对每个板块做归组判断（调用 output_layer.rules.classify_group）
#   2. 合并 stock_candidates（升级 stock_mentions → 含正宗度占位字段）
#   3. 构建 top_sectors / hidden_signals / market_context / final_recommendations
# 输入：scored_sectors（dual_score 输出，不含 group 字段）+ context dict
# 输出：editorial_result dict
# 被谁调用：analyzer._analyze()

from output_layer.conclusions import make_group_conclusion
from editorial_layer.stock_merger import merge_stock_candidates
from editorial_layer.sector_builder import build_top_sectors, build_hidden_signals
from editorial_layer.market_context import build_market_context
from editorial_layer.recommendations import build_final_recommendations


def build_editorial(scored_sectors: list, context: dict = None) -> dict:
    """
    编辑层主入口。

    scored_sectors : dual_score 层输出的板块列表（含双评分字段，不含 group）
    context        : {date, confidence, dedup_stats, hotrank_signals, source_stats}
    返回 editorial_result dict。
    """
    if context is None:
        context = {}

    # ── 1. 归组判断（复用 output_layer.rules.classify_group）────
    sectors_with_group = [make_group_conclusion(s) for s in scored_sectors]

    # ── 2. 合并 stock_candidates（添加正宗度占位字段）──────────
    sectors_full        = []
    stock_pool_by_sector: dict = {}

    for s in sectors_with_group:
        candidates = merge_stock_candidates(s)
        s_full     = {**s, 'stock_candidates': candidates}
        sectors_full.append(s_full)
        stock_pool_by_sector[s['name']] = candidates

    # ── 3. 构建各视图 ─────────────────────────────────────────
    top_sectors          = build_top_sectors(sectors_full)
    hidden_signals       = build_hidden_signals(context.get('hotrank_signals', []))
    market_context       = build_market_context(context)
    final_recommendations = build_final_recommendations(sectors_full)

    return {
        # 透传上下文字段
        'date':                   context.get('date', ''),
        'confidence':             context.get('confidence', 'unknown'),
        'source_stats':           context.get('source_stats', []),
        'dedup_stats':            context.get('dedup_stats', {}),
        'hotrank_signals':        context.get('hotrank_signals', []),
        # 编辑层产出
        'market_context':         market_context,
        'top_sectors':            top_sectors,
        'hidden_signals':         hidden_signals,
        'stock_pool_by_sector':   stock_pool_by_sector,
        'final_recommendations':  final_recommendations,
        'all_sectors':            sectors_full,
    }
