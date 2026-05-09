# 编辑层下游消费接口
# 供外部直接访问 editorial_result 各子对象
# 被谁调用：外部消费方 / 测试


def get_market_context(editorial_result: dict) -> dict:
    return editorial_result['market_context']


def get_top_sectors(editorial_result: dict) -> list:
    return editorial_result['top_sectors']


def get_hidden_signals(editorial_result: dict) -> list:
    return editorial_result['hidden_signals']


def get_stock_pool_by_sector(editorial_result: dict) -> dict:
    return editorial_result['stock_pool_by_sector']


def get_final_recommendations(editorial_result: dict) -> dict:
    return editorial_result['final_recommendations']


def get_all_sectors(editorial_result: dict) -> list:
    return editorial_result['all_sectors']
