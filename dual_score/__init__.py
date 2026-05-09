# 双评分层包入口
# 主调用链入口：score_sectors(sectors) → dual_score_result
# 两个评分分支（continuation / fermentation）各自独立，由 entry.py 统一编排

from dual_score.entry import score_sectors
from dual_score.continuation import score_continuation
from dual_score.fermentation import score_fermentation
from dual_score.output import build_dual_score_output
from dual_score.downstream import get_scored_sectors, get_scoring_stats
from dual_score.report import format_summary as format_dual_score_summary

__all__ = [
    # 主调用链
    'score_sectors',
    # 包内子模块供单元测试或工具调用
    'score_continuation', 'score_fermentation',
    'build_dual_score_output',
    'get_scored_sectors', 'get_scoring_stats',
    'format_dual_score_summary',
]
