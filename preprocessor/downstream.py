# 下游消费接口
# 输入：preprocessor/output.py 的结果 dict
# 输出：processed_items 列表 / stats dict
# 被谁调用：analyzer.py（_analyze 管道）


def get_processed_items(result: dict) -> list:
    return result['processed_items']


def get_stats(result: dict) -> dict:
    return result['stats']


def get_logic_units(result: dict) -> list:
    return result.get('logic_units', [])


def get_signal_stats(result: dict) -> dict:
    return result.get('signal_stats', {})


def get_dedup_decisions(result: dict) -> list:
    return result.get('dedup_decisions', [])
