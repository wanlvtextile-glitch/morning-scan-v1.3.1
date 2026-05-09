# 分析层结构化输出
# 输入：各聚类/评分结果
# 输出：analysis_result dict（写文件前的最终结构）
# 被谁调用：analysis/entry.py

from datetime import datetime


def build_analysis_output(
    confidence: str,
    source_stats: list,
    dedup_stats: dict,
    sectors: list,
    hotrank: list,
    hotrank_signals: list,
    unmatched_count: int,
) -> dict:
    return {
        'generated_at':   datetime.now().isoformat(),
        'confidence':     confidence,
        'source_stats':   source_stats,
        'dedup_stats':    dedup_stats,
        'sectors':        sectors,
        'hotrank':        hotrank[:20],
        'hotrank_signals': hotrank_signals,
        'unmatched_count': unmatched_count,
    }
