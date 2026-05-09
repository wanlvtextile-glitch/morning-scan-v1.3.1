# 结构化输出层
# 输入：scored_sectors（每个 sector 已追加双评分字段）
# 输出：dual_score_result dict（含 scored_sectors + scoring_stats）
# 被谁调用：dual_score/entry.py


def _count_scores(scored_sectors: list, field: str) -> dict:
    """统计某个评分字段各档位（高/中/低）的板块数量"""
    counts = {'高': 0, '中': 0, '低': 0}
    for s in scored_sectors:
        val = s.get(field)
        if val in counts:
            counts[val] += 1
    return counts


def build_dual_score_output(scored_sectors: list) -> dict:
    """
    构建双评分层结果对象。

    scored_sectors  : 每个板块已追加 continuation_score / fermentation_score 等字段
    scoring_stats   : 各评分档位分布，供日志和下游消费快速统计
    """
    return {
        'scored_sectors': scored_sectors,
        'scoring_stats': {
            'continuation':  _count_scores(scored_sectors, 'continuation_score'),
            'fermentation':  _count_scores(scored_sectors, 'fermentation_score'),
        },
    }
