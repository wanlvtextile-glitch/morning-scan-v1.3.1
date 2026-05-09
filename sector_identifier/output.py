# 结构化输出层
# 输入：板块聚类各中间变量
# 输出：sector_result dict（题材识别结果对象）
#       字段：sector_weighted / sector_matched_kws / unmatched / hotrank_list / sector_to_hotrank
# 被谁调用：sector_identifier/entry.py


def build_sector_output(
    sector_weighted: dict,
    sector_matched_kws: dict,
    unmatched: list,
    hotrank_list: list,
    sector_to_hotrank: dict,
) -> dict:
    return {
        'sector_weighted':    dict(sector_weighted),
        'sector_matched_kws': {k: sorted(v) for k, v in sector_matched_kws.items()},
        'unmatched':          unmatched,
        'hotrank_list':       hotrank_list,
        'sector_to_hotrank':  sector_to_hotrank,
    }
