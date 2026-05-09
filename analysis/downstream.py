# 分析层下游消费接口
# 输入：analysis/output.py 的结果 dict
# 被谁调用：SKILL.md 报告步骤、外部消费方


def get_sectors(result: dict) -> list:
    return result['sectors']


def get_hotrank(result: dict) -> list:
    return result['hotrank']


def get_hotrank_signals(result: dict) -> list:
    return result['hotrank_signals']


def get_dedup_stats(result: dict) -> dict:
    return result['dedup_stats']


def get_confidence(result: dict) -> str:
    return result['confidence']
