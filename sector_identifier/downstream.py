# 下游消费接口
# 输入：sector_identifier/output.py 的结果 dict
# 被谁调用：analyzer.py（_analyze 管道）


def get_sector_weighted(result: dict) -> dict:
    return result['sector_weighted']


def get_sector_matched_kws(result: dict) -> dict:
    return result['sector_matched_kws']


def get_unmatched(result: dict) -> list:
    return result['unmatched']


def get_hotrank_list(result: dict) -> list:
    return result['hotrank_list']


def get_sector_to_hotrank(result: dict) -> dict:
    return result['sector_to_hotrank']
