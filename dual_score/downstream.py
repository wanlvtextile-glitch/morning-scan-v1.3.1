# 下游消费接口
# 输入：dual_score_result（dual_score/entry.py 的输出对象）
# 返回：scored_sectors list / scoring_stats dict
# 被谁调用：analyzer._analyze()（日志打印），未来输出层


def get_scored_sectors(dual_score_result: dict) -> list:
    return dual_score_result['scored_sectors']


def get_scoring_stats(dual_score_result: dict) -> dict:
    return dual_score_result['scoring_stats']
