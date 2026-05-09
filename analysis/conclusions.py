# 分析层中间结论
# 输入：板块摘要 dict（含所有聚类字段）
# 输出：{stage, stage_signals, star_rating} 追加到板块 dict
# 被谁调用：analysis/entry.py

from analysis.scorer import compute_star_rating
from analysis.stage_rules import apply_stage_rules


def make_sector_analysis(sector: dict) -> dict:
    """对单个板块 dict 追加评分和阶段结论，返回新 dict（不修改原始输入）。"""
    star  = compute_star_rating(
        sector['effective_count'],
        sector['source_count'],
        sector['hotrank']['rank'] if sector.get('hotrank') else None,
    )
    stage, signals = apply_stage_rules(sector)
    return {
        **sector,
        'star_rating':   star,
        'stage':         stage,
        'stage_signals': signals,
    }
