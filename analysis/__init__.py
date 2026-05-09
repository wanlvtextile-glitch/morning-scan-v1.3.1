# 分析层包入口
# 主调用链入口：run_analysis_pipeline(sector_result, ...) → analysis_result
# 其余导出为向后兼容，供旧路径 from analyzer import X 继续有效

from analysis.scorer import compute_star_rating
from analysis.stage_rules import apply_stage_rules, compute_stage
from analysis.stage_definitions import STAGES, STAGE_LABELS
from analysis.conclusions import make_sector_analysis
from analysis.output import build_analysis_output
from analysis.downstream import (
    get_sectors, get_hotrank, get_hotrank_signals,
    get_dedup_stats, get_confidence,
)
from analysis.report import format_summary as format_analysis_summary
from analysis.entry import (
    load_stock_names, extract_stock_mentions,
    build_sector_summaries, build_hotrank_only,
    build_hotrank_signals, run_analysis_pipeline,
)

__all__ = [
    # 主调用链
    'run_analysis_pipeline',
    # 向后兼容（旧路径 from analyzer import X 继续有效）
    'compute_star_rating', 'compute_stage',
    'load_stock_names', 'extract_stock_mentions',
    # 包内子模块供单元测试或工具调用
    'apply_stage_rules', 'STAGES', 'STAGE_LABELS',
    'make_sector_analysis', 'build_analysis_output',
    'get_sectors', 'get_hotrank', 'get_hotrank_signals',
    'get_dedup_stats', 'get_confidence',
    'format_analysis_summary',
    'build_sector_summaries', 'build_hotrank_only',
    'build_hotrank_signals',
]
