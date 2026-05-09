# 热度评分模块
# 输入：effective_count, source_count, hotrank_pos
# 输出：star_rating (int 1-5)
# 被谁调用：analysis/entry.py，analyzer.py（通过 compute_star_rating 别名）


def compute_star_rating(effective_count: float,
                        source_count: int,
                        hotrank_pos: int | None) -> int:
    """
    ⭐⭐⭐⭐⭐ 多源爆发 + 人气榜 Top3 + 有效量充足
    ⭐⭐⭐⭐   3源以上有效量充足，或 2源以上 + 人气榜前10
    ⭐⭐⭐     2源以上，或有效量 >= 5
    ⭐⭐       有效量 >= 2
    ⭐        仅人气榜信号（hotrank_only 补建）
    """
    pos = hotrank_pos if hotrank_pos is not None else 999
    if source_count >= 3 and pos <= 3 and effective_count >= 8:
        return 5
    if source_count >= 3 and effective_count >= 8:
        return 4
    if source_count >= 2 and pos <= 10:
        return 4
    if source_count >= 2 and effective_count >= 8:
        return 4
    if source_count >= 2 or effective_count >= 5:
        return 3
    if effective_count >= 2:
        return 2
    return 1
