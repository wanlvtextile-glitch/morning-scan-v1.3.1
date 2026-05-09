# 下游消费接口
# 输入：preprocessor/output.py 的结果 dict
# 输出：processed_items 列表 / stats dict
# 被谁调用：analyzer.py（_analyze 管道）


def get_processed_items(result: dict) -> list:
    return result['processed_items']


def get_stats(result: dict) -> dict:
    return result['stats']
