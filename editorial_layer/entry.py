from output_layer.conclusions import make_group_conclusion
from editorial_layer.logic_summary import attach_logic_summary
from editorial_layer.stock_merger import merge_stock_candidates
from editorial_layer.sector_builder import build_top_sectors, build_hidden_signals
from editorial_layer.market_context import build_market_context
from editorial_layer.recommendations import build_final_recommendations


def build_editorial(scored_sectors: list, context: dict = None) -> dict:
    """Build the editorial layer from scored sectors."""
    if context is None:
        context = {}

    sectors_with_group = [make_group_conclusion(s) for s in scored_sectors]

    sectors_full = []
    stock_pool_by_sector: dict = {}

    for sector in sectors_with_group:
        candidates = merge_stock_candidates(sector)
        sector_full = attach_logic_summary({**sector, 'stock_candidates': candidates})
        sectors_full.append(sector_full)
        stock_pool_by_sector[sector['name']] = candidates

    top_sectors = build_top_sectors(sectors_full)
    hidden_signals = build_hidden_signals(context.get('hotrank_signals', []))
    market_context = build_market_context(context)
    final_recommendations = build_final_recommendations(sectors_full)

    return {
        'date': context.get('date', ''),
        'confidence': context.get('confidence', 'unknown'),
        'source_stats': context.get('source_stats', []),
        'dedup_stats': context.get('dedup_stats', {}),
        'hotrank_signals': context.get('hotrank_signals', []),
        'market_context': market_context,
        'top_sectors': top_sectors,
        'hidden_signals': hidden_signals,
        'stock_pool_by_sector': stock_pool_by_sector,
        'final_recommendations': final_recommendations,
        'all_sectors': sectors_full,
    }
